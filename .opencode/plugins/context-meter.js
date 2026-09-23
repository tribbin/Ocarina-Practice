// Context meter: writes the session's context usage to
// .opencode/context-usage.json after every assistant message, so any
// running session (or Robin) can read the actual numbers instead of the
// model guessing where it stands. The watch/action lines below are Robin's
// observed quality thresholds for glm53@vibe (AGENTS.md rule 18).
//
// The file holds the LAST assistant message's accounting — its input+cache
// tokens ARE the context that message was fed (cumulative for the whole
// conversation), so it is the live context gauge.
//
// Everything this plugin does logs through client.app.log: a meter that
// fails silently is worthless (the repo's own anti-silent-catch rule).

const LINES = { watch: 300000, action: 350000, hard: 400000 };
const DEBUG_DUMP_MAX = 5; // calibration: dump the first N message events

function num(x) {
  return typeof x === "number" && isFinite(x) ? x : 0;
}

export const ContextMeterPlugin = async ({ client, worktree }) => {
  const log = async (level, message, extra) => {
    try {
      await client.app.log({
        service: "context-meter",
        level,
        message,
        extra: extra === undefined ? undefined : extra,
      });
    } catch (e) {}
  };
  await log("info", "initialized", { worktree: worktree || null, lines: LINES });

  let debugDumped = 0;
  let last = { used: -1, at: 0 };

  const write = async (payload) => {
    try {
      const fs = await import("node:fs/promises");
      const path = await import("node:path");
      const dir = path.join(worktree || ".", ".opencode");
      await fs.mkdir(dir, { recursive: true });
      await fs.writeFile(
        path.join(dir, "context-usage.json"),
        JSON.stringify(payload, null, 2),
      );
    } catch (e) {
      await log("error", "write failed", { cause: String(e && e.message || e) });
    }
  };

  const decode = (event) => {
    const props = event.properties || {};
    const m = props.message || props.info || event.message;
    if (!m || m.role !== "assistant") return null;
    // Field-name shapes have drifted between versions; pick the first
    // present group rather than mixing templates.
    const t = m.tokens || m.tokenCount || {};
    const cache = t.cache || m.cache || {};
    const pick = (...xs) => {
      for (const x of xs) if (x != null && isFinite(+x)) return num(x);
      return 0;
    };
    const input = pick(t.input, t.promptTokens, t.prompt);
    const cacheRead = pick(cache.read, t.cacheRead, cache.creation);
    const cacheWrite = pick(cache.write, t.cacheWrite);
    const output = pick(t.output, t.completionTokens, t.completion);
    const reasoning = pick(t.reasoning);
    // The API's own total wins when present (validated against the vibe
    // stream 2026-09-23: tokens.total === input+cache.read+cache.write+
    // output+reasoning); the sum is the fallback for shapes without it.
    const used = pick(t.total) ||
      input + cacheRead + cacheWrite + output + reasoning;
    return { m, tokens: { input, cache_read: cacheRead, cache_write: cacheWrite,
                          output, reasoning }, used };
  };

  const dumpDebug = async (event, fit) => {
    // Calibration aid: the first few message payloads, keys + token shape.
    try {
      const props = event.properties || {};
      const m = props.message || props.info || event.message;
      if (!m) return;
      const fs = await import("node:fs/promises");
      const path = await import("node:path");
      const dir = path.join(worktree || ".", ".opencode");
      await fs.mkdir(dir, { recursive: true });
      const file = path.join(dir, "context-usage.debug.json");
      let list = [];
      try { list = JSON.parse(await fs.readFile(file, "utf8")); } catch (e) {}
      list.push({
        at: new Date().toISOString(),
        topKeys: Object.keys(props),
        msgKeys: Object.keys(m),
        fit: fit || null,
        tokensRaw: m.tokens !== undefined ? m.tokens : ("absent; m=" +
          JSON.stringify(Object.fromEntries(Object.entries(m).slice(0, 20)))
          ).slice(0, 800),
      });
      if (list.length > DEBUG_DUMP_MAX) {
        await fs.writeFile(file, JSON.stringify(list, null, 2));
        return;
      }
      await log("info", "message payload calibration", { n: list.length });
      await fs.writeFile(file, JSON.stringify(list, null, 2));
    } catch (e) {
      await log("warn", "debug dump failed", { cause: String(e) });
    }
  };

  return {
    event: async ({ event }) => {
      if (event.type !== "message.updated") return;
      const d = decode(event);
      if (debugDumped < DEBUG_DUMP_MAX) { debugDumped++; await dumpDebug(event, d); }
      if (!d || !d.used) return;
      const now = Date.now();
      if (d.used === last.used && now - last.at < 30000) return;
      last = { used: d.used, at: now };
      const zone = d.used >= LINES.hard ? "hard"
        : d.used >= LINES.action ? "action"
        : d.used >= LINES.watch ? "watch" : "ok";
      await write({
        session: d.m.sessionID || d.m.sessionId || "",
        model: d.m.modelID || d.m.model || "",
        context_est: d.used,
        zone: zone,
        lines: LINES,
        tokens: d.tokens,
        at: new Date().toISOString(),
      });
    },
  };
};
