// Offline shell (service worker) for the ocarina practice tool. Registered
// from js/app.js on window load; best-effort everywhere else.
//
// The precache set is maintained without editing this file: the core shell is
// listed by hand (one line per shipped file), the per-instrument data is
// DERIVED from instruments.json at install — every ocarina's fingerings,
// body template, song-specific template overrides and best-effort tone model
// (an absent tone.json is a legitimate "no recordings yet", never an error).
// Only delivering OK responses are cached; 404s stay 404s.
//
// Update flavor: navigations go network-first (fresh HTML when online, the
// cached shell offline); everything else is stale-while-revalidate — served
// instantly from cache while a background refetch keeps the cache current,
// so a deployed update is live on the SECOND visit. skipWaiting/claim makes
// the new worker take over right away.
const VERSION = "oco-pwa-v48";
const CORE = [
  "index.html",
  "manifest.webmanifest",
  "css/app.css?v=css-v3",
  "favicon.svg",
  "js/parse.js",
  "js/music-math.js",
  "js/ocarina.js",
  "js/audio.js",
  "js/library.js",
  "js/ui.js",
  "js/practice.js",
  "js/pitch-dsp.js",
  "js/pitch-ac-worker.js",
  "js/app.js",
  "js/debug.js",
];

function cacheOf() {
  return caches.open(VERSION);
}

// Delivering-OKs-only fetcher: a 404 (tone.json "no recordings yet") or a
// failed fetch must never poison the cache.
async function fillFrom(paths) {
  const c = await cacheOf();
  await Promise.all(paths.map(async p => {
    try {
      const res = await fetch(p, { cache: "no-cache" });
      if (res.ok) await c.put(p, res);
    } catch (e) {} // best-effort: missing pieces simply stay online-fetched
  }));
}

// Released data rides NETWORK-FIRST with a cached fallback (Robin,
// 2026-09-28: the new songs never came up by a phone refresh —
// stale-while-revalidate serves app content one reload late, and a resumed
// phone app never re-checked at all). Songs, the instrument manifest and
// every instrument's tone/twin model are the content the player expects
// current the moment a load lands: online = always fresh, offline = the
// cached copy, and a legitimate 404 (declared-but-absent tone.json) passes
// through uncached exactly as today.
const DATA_NETWORK_FIRST =
  /(?:^|\/)(?:songs|instruments)\.json$|(?:^|\/)instruments\/[^/]+\/(?:tone|twin_model)\.json$/;

// Cache writes are scheme-gated: file: origins (VS Code browser preview,
// opened-from-disk) reject Cache.put at the engine level; nothing here may
// throw out of a handler.
async function putOk(cache, key, res) {
  if (!res || !res.ok || !/^https?:$/.test(self.location.protocol)) return;
  try { await cache.put(key, res); } catch (e) {}
}

self.addEventListener("install", (e) => {
  // No cache work on non-HTTP(S) contexts: opened from disk (VS Code browser
  // preview, double-click) the fetches behind addAll are scheme-unsupported
  // and would throw out of the install. Offline mode is a served-page
  // feature; a file-scheme page just skips it quietly.
  if (!/^https?:$/.test(self.location.protocol)) return;
  self.skipWaiting();
  e.waitUntil((async () => {
    const c = await cacheOf();
    // Core shell must exist to the letter — a failed addAll fails the install
    // loudly (offline mode would be broken anyway, so failing is honest).
    await c.addAll(CORE);
    try {
      const manifest = await (await fetch("instruments.json", { cache: "no-cache" })).json();
      const paths = new Set(["instruments.json", "songs.json"]);
      for (const inst of (manifest.instruments || [])) {
        const own = [inst.fingerings, inst.svg,
                     ...(inst.svgWhen || []).map(r => r.svg), inst.tone,
                     inst.twin];
        for (const p of own) {
          if (typeof p === "string" && p) paths.add(p);
        }
      }
      await fillFrom([...paths]);
    } catch (err) {
      console.warn("[sw] instrument cache derive skipped:", err);
    }
  })());
});

self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  let url;
  try { url = new URL(req.url); } catch (err) { return; }
  if (url.origin !== self.location.origin) return;

  if (req.mode === "navigate") {
    e.respondWith((async () => {
      try {
        const res = await fetch(req);
        if (res.ok) putOk(await cacheOf(), "index.html", res.clone());
        return res;
      } catch (err) {
        const c = await cacheOf();
        return (await c.match("index.html")) ||
          new Response("Offline and the shell is not cached yet.", { status: 503 });
      }
    })());
    return;
  }

  if (DATA_NETWORK_FIRST.test(url.pathname)) {
    e.respondWith((async () => {
      const c = await cacheOf();
      try {
        // cache:"no-cache" forces revalidation — the browser HTTP cache's
        // heuristic freshness (10% of the served file's age) once answered
        // these with a stale-200 for a >1 h window (observed 2026-09-28: a
        // deployed songs.json never reached the page despite the SW's
        // network-first branch), and Pages deploys ship max-age=600 on top.
        const res = await fetch(req, { cache: "no-cache" });
        if (res.ok) await putOk(c, req, res.clone());
        return res;
      } catch (err) {
        const hit = await c.match(req);
        if (hit) return hit;
        return new Response("Offline and the data copy is not cached yet.",
          { status: 504 });
      }
    })());
    return;
  }

  // Stale-while-revalidate for every other same-origin GET.
  e.respondWith((async () => {
    const c = await cacheOf();
    const hit = await c.match(req);
    if (hit) {
      // Refresh in the background; serving never waits on the network.
      e.waitUntil(fillFrom([url.pathname + url.search]));
      return hit;
    }
    try {
      const res = await fetch(req);
      await putOk(c, req, res.clone());
      return res;
    } catch (err) {
      return new Response("Offline and not cached yet.", { status: 504 });
    }
  })());
});
