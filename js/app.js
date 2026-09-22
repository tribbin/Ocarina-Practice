// Global error net: uncaught window errors and unhandled promise rejections
// land in #err as appended lines — the messages render()/boot() put there
// must survive (both sides write the same node, so overwriting here would
// wipe theirs and overwrite-by-them would drop a crash report).
function reportGlobalError(label, detail, error) {
  const el = document.getElementById("err");
  if (!el) return;
  const line = document.createElement("div");
  let text = label + ": " + (detail || "unknown error");
  if (error && error.stack) {
    // The stack's 2nd line names the throw site (1st repeats the message).
    const frame = String(error.stack).split("\n")[1];
    if (frame) text += " — " + frame.trim();
  }
  line.textContent = text;
  el.appendChild(line);
}
window.onerror = function(m, s, l, c, error) {
  reportGlobalError("window error", (m || "unknown") + " @" + (s || "?") + ":" + l, error);
};
window.addEventListener("unhandledrejection", (ev) => {
  const r = ev.reason;
  reportGlobalError("unhandled rejection",
                    r instanceof Error ? r.message : String(r), r instanceof Error ? r : null);
});

function installFingerings(fing) {
  window.FING = fing;
  window.NOTES = fing.notes.map(n => n.id);
  window.DISPLAY = Object.fromEntries(fing.notes.map(n => [n.id, n.display]));
  window.CHAMBER = Object.fromEntries(fing.notes.map(n => [n.id, n.chamber]));
  window.COVER = Object.fromEntries(fing.notes.map(n => [n.id, n.covered]));
  const root = document.documentElement;
  const chambers = fing.chambers || {};
  for (const [id, cfg] of Object.entries(chambers)) {
    if (cfg && cfg.color) root.style.setProperty("--ch" + id, cfg.color);
  }
}

async function loadText(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error("Could not load " + path + " (" + res.status + ")");
  return res.text();
}

async function loadJson(path) {
  return JSON.parse(await loadText(path));
}

const TPL_CACHE = {};
let installedTplPath = "";
let tplSyncing = null;
// Instrument-load generation: each loadInstrument bumps it, and only the run
// belonging to the newest switch may install. Without this, a slow older
// fetch resolves LAST and overwrites the newer instrument's fingerings and
// template (rapid dropdown swaps ended on the wrong ocarina).
let instLoadGen = 0;

function currentSongId() {
  const sel = document.getElementById("scale");
  return (sel && sel.value) || "";
}

function currentSongTitle() {
  const ta = document.getElementById("src");
  if (!ta || typeof titleFromText !== "function") return "";
  return String(titleFromText(ta.value) || "").trim();
}

function songMatchesStem(stem, id, title) {
  if (!stem) return true;
  if (id === stem || (id && id.startsWith(stem + "-"))) return true;
  if (stem === "sarias-song" && /^saria'?s song$/i.test(title)) return true;
  return false;
}

function currentTemplatePath() {
  const inst = window.CURRENT_INSTRUMENT;
  if (!inst) return "";
  const theme = document.documentElement.getAttribute("data-theme") || "";
  const id = currentSongId();
  const title = currentSongTitle();
  for (const rule of (inst.svgWhen || [])) {
    if (rule.theme && rule.theme !== theme) continue;
    if (rule.song && !songMatchesStem(rule.song, id, title)) continue;
    if (rule.svg) return rule.svg;
  }
  return inst.svg;
}

function loadTemplateText(path) {
  if (!TPL_CACHE[path]) TPL_CACHE[path] = loadText(path);
  return TPL_CACHE[path];
}

function ensureOcarinaTemplate() {
  const path = currentTemplatePath();
  if (!path || path === installedTplPath) return Promise.resolve(false);
  if (tplSyncing) return tplSyncing;
  tplSyncing = loadTemplateText(path).then(text => {
    installOcarinaTemplate(text);
    installedTplPath = path;
    tplSyncing = null;
    return true;
  }).catch(err => {
    tplSyncing = null;
    console.error(err);
    return false;
  });
  return tplSyncing;
}

async function loadInstrument(inst) {
  const gen = ++instLoadGen;
  const [fing, svgText] = await Promise.all([
    loadJson(inst.fingerings),
    loadText(inst.svg)
  ]);
  if (gen !== instLoadGen) return false;   // superseded by a newer switch
  installFingerings(fing);
  installOcarinaTemplate(svgText);
  installedTplPath = inst.svg;
  TPL_CACHE[inst.svg] = Promise.resolve(svgText);
  window.CURRENT_INSTRUMENT = inst;
  await ensureOcarinaTemplate();
  // Per-ocarina tone model (instruments/<id>/tone.json — fitted per-chamber
  // anchors, see instruments/README.md). A 404 is normal: the ocarina has no
  // recordings yet and keeps the baked-in generic model. installToneModel
  // resets on failure so a stale model never leaks across instrument swaps;
  // the CURRENT_INSTRUMENT check keeps a slower old fetch from clobbering a
  // newer instrument's install.
  if (typeof installToneModel !== "function") return;
  try {
    const tone = inst.tone ? await loadJson(inst.tone) : null;
    if (window.CURRENT_INSTRUMENT === inst) installToneModel(tone, inst.id);
  } catch (e) {
    if (window.CURRENT_INSTRUMENT === inst) installToneModel(null, inst.id);
  }
}

// Visual themes live as `data-theme` on <html>. Chamber colors are not part of
// a theme — they stay the fingering-data symbology. `?oot` is the hidden
// Hyrule Field preview; later a model can pass its id here (e.g. inst.theme).
// Shared zen links carry `?inst=<ocarina id>&song=<library id>&zen=1`.
function queryParam(name) {
  try { return new URLSearchParams(location.search).get(name) || ""; }
  catch (e) { return ""; }
}

function queryHas(name) {
  try { return new URLSearchParams(location.search).has(name); }
  catch (e) { return false; }
}

function themeFromQuery() {
  return queryHas("oot") ? "oot" : "";
}

function applyTheme(name) {
  const html = document.documentElement;
  if (name) html.setAttribute("data-theme", name);
  else html.removeAttribute("data-theme");
}

function instLabel(inst) {
  const parts = [inst.type, inst.version].filter(Boolean);
  let label = parts.join(" · ");
  if (inst.range) label += " (" + inst.range + ")";
  return label;
}

function fillInstrumentSelect(selectedId) {
  const sel = document.getElementById("instSel");
  if (!sel) return;
  sel.innerHTML = "";
  for (const inst of (window.INSTRUMENTS || [])) {
    const o = document.createElement("option");
    o.value = inst.id;
    o.textContent = instLabel(inst);
    if (inst.id === selectedId) o.selected = true;
    sel.appendChild(o);
  }
}

async function switchInstrument(inst) {
  const installed = await loadInstrument(inst);
  if (installed === false) return;   // a newer switch superseded this one
  // The ocarina swap may invalidate the workout targets: end any practice
  // session so the next engagement starts fresh on the new instrument.
  if (typeof practiceInvalidate === "function") try { practiceInvalidate(); } catch (e) {}
  buildKB();
  if (typeof fillLibrary === "function") fillLibrary();
  else if (typeof syncLibraryMenu === "function") syncLibraryMenu();
  if (typeof render === "function") render();
}

function wireInstrumentPicker() {
  const sel = document.getElementById("instSel");
  if (!sel) return;
  sel.addEventListener("change", async () => {
    const inst = (window.INSTRUMENTS || []).find(i => i.id === sel.value);
    if (inst) await switchInstrument(inst);
  });
}

async function boot() {
  try {
    applyTheme(themeFromQuery());
    const [manifest, songs, cssText] = await Promise.all([
      loadJson("instruments.json"),
      loadJson("songs.json"),
      loadText("css/app.css")
    ]);
    APP_CSS = cssText;
    window.INSTRUMENTS = manifest.instruments || [];
    const instParam = queryParam("inst");
    const chosen = (instParam && INSTRUMENTS.find(i => i.id === instParam))
      || INSTRUMENTS.find(i => i.id === manifest.default) || INSTRUMENTS[0];
    if (!chosen) throw new Error("No instruments defined in instruments.json");
    await loadInstrument(chosen);
    fillInstrumentSelect(chosen.id);
    wireInstrumentPicker();
    initBuiltin(songs);
    wireLibrary();
    wireUi();
    buildKB();
    const songParam = queryParam("song");
    if (songParam && (BUILTIN[songParam] || (typeof userLib === "function" && userLib()[songParam]))) {
      // The linked song loads even when the range filter hides it from the
      // dropdown (e.g. shared with another ocarina) — fillLibrary just can't
      // highlight it there.
      fillLibrary(songParam);
      loadLibraryItem(songParam);
    } else {
      fillLibrary("major");
      loadLibraryItem("major");
    }
    if (queryHas("zen")) enterZenFromLink();
  } catch (err) {
    const e = document.getElementById("err");
    if (e) {
      e.textContent = (err && err.message ? err.message : String(err)) +
        " — serve this folder over HTTP, e.g. python3 -m http.server";
    }
    console.error(err);
  }
}

boot();
