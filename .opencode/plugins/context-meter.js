// Context meter: writes the session's context usage to
// .opencode/context-usage.json after every assistant message, so any
// running session (or Robin) can read the actual numbers instead of the
// model guessing where it stands. The watch/action lines below are Robin's
// observed quality thresholds for glm53@vibe (AGENTS.md rule 18).
//
// The file holds the LAST assistant message's accounting — its input+cache
// tokens ARE the context that message was fed (cumulative for the whole
// conversation), so it is the live context gauge.

const LINES = { watch: 300000, action: 350000, hard: 400000 };

function num(x) {
  return typeof x === "number" && isFinite(x) ? x : 0;
}

export const ContextMeterPlugin = async ({ worktree, $ }) => {
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
      // A meter that fails must never disturb the session — stay silent.
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
    const input = pick(t.input, t.promptTokens);
    const cacheRead = pick(cache.read, t.cacheRead, cache.creation);
    const cacheWrite = pick(cache.write, t.cacheWrite);
    const output = pick(t.output, t.completionTokens);
    const reasoning = pick(t.reasoning);
    const used = input + cacheRead + cacheWrite + output + reasoning;
    if (!used) return null;
    return { m, tokens: { input, cache_read: cacheRead, cache_write: cacheWrite,
                          output, reasoning }, used };
  };

  return {
    event: async ({ event }) => {
      if (event.type !== "message.updated") return;
      const d = decode(event);
      if (!d) return;
      const now = Date.now();
      // Throttle: only on a changed total and at most ~2 skips per minute.
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
