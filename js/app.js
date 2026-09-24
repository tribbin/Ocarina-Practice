import { titleFromText } from "./parse.js";
import { installOcarinaTemplate, invalidateSvgHtml } from "./ocarina.js";
import { installToneModel } from "./audio.js";
import { BUILTIN, fillLibrary, initBuiltin, loadLibraryItem, refreshGeneratedScales,
         syncLibraryMenu, userLib, wireLibrary } from "./library.js";
import { buildKB, enterZenFromLink, render, setAppCss, wireUi } from "./ui.js";
import { practiceInvalidate } from "./practice.js";
import "./debug.js";

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
  // The C-major/chromatic library entries live off the loaded chart —
  // regenerate them for the newly installed instrument (never shipped data).
  refreshGeneratedScales(window.NOTES);
  // Hole/chamber data feeds the card-svg memoization; a fresh fingering set
  // alone is enough to end every stored rendering.
  if (typeof invalidateSvgHtml === "function") invalidateSvgHtml();
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
export let installedTplPath = "";
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

function songMatchesStem(stem, id, title, titleRe) {
  if (!stem) return true;
  if (id === stem || (id && id.startsWith(stem + "-"))) return true;
  if (titleRe && titleRe.test(title)) return true;
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
    // A rule may match by song id, origin stem, or — via songTitle — by the
    // song's title text (each rule owns its own title condition).
    if (rule.songTitle) {
      let titleRe = null;
      try { titleRe = new RegExp(rule.songTitle, "i"); }
      catch (e) { continue; } // broken manifest entry: skip, never crash render
      if (rule.song && !songMatchesStem(rule.song, id, title, titleRe)) continue;
      if (!rule.song && !titleRe.test(title)) continue;
    } else if (rule.song && !songMatchesStem(rule.song, id, title)) continue;
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
    const ok = installOcarinaTemplate(text);  // false: unparsable SVG text
    // Mark the path consumed either way — a failure must never re-arm the
    // render loop by looking "not yet installed" forever.
    installedTplPath = path;
    tplSyncing = null;
    return ok;
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
  // ?plain / ?oot stay honored per shared link; without them the SAVED choice
  // rules (the Hyrule look stays the default for a fresh browser). The toggle
  // beside Clear rides the same key ("oco-theme").
  if (queryHas("plain")) return "";
  if (queryHas("oot")) return "oot";
  try {
    const saved = localStorage.getItem("oco-theme");
    if (saved === "" || saved === "oot") return saved;
  } catch (e) {}
  return "oot";
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
    setAppCss(cssText);
    window.INSTRUMENTS = manifest.instruments || [];
    // Manifest sanity: a duplicated id makes the picker ambiguous (two
    // indistinguishable entries) — say so instead of silently picking the
    // first match; a bogus ?inst id would otherwise fall back invisible.
    {
      const seen = new Set(), dups = [];
      for (const inst of window.INSTRUMENTS) {
        if (inst && inst.id) {
          if (seen.has(inst.id)) dups.push(inst.id);
          else seen.add(inst.id);
        }
      }
      if (dups.length) {
        reportGlobalError("boot", "instruments.json repeats ocarina id(s): " + dups.join(", "));
      }
    }
    const instParam = queryParam("inst");
    if (instParam && !window.INSTRUMENTS.some(i => i.id === instParam)) {
      reportGlobalError("boot", "Unknown ocarina id \u2018" + instParam +
        "\u2019 — using the default instrument instead.");
    }
    const chosen = (instParam && INSTRUMENTS.find(i => i.id === instParam))
      || INSTRUMENTS.find(i => i.id === manifest.default) || INSTRUMENTS[0];
    if (!chosen) throw new Error("No instruments defined in instruments.json");
    // initBuiltin runs BEFORE the first instrument install: the generated
    // scale entries refresh off the chart mid-install and must mutate the
    // final BUILTIN object, not one initBuiltin is about to replace.
    initBuiltin(songs);
    await loadInstrument(chosen);
    fillInstrumentSelect(chosen.id);
    wireInstrumentPicker();
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
      // First visit territory: the Alto C's own Song of Storms is the home
      // song; fall back to the major scale if the id is ever missing.
      const home = BUILTIN["song-of-storms"] ? "song-of-storms" : "major";
      fillLibrary(home);
      loadLibraryItem(home);
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

// Offline mode: the service worker (sw.js) serves the shell, song data and
// the ocarinas' fingerings/templates from cache, with background refresh for
// updates. Best-effort by design — plain http:// (no secure context) and
// browsers without the API simply skip it; a failed registration must never
// reach the app.
window.addEventListener("load", () => {
  // Only serve over HTTP(S): a file-scheme page (VS Code preview) has no
  // service worker cache to offer.
  if (!/^https?:$/.test(location.protocol)) return;
  if (!navigator.serviceWorker) return;
  try { navigator.serviceWorker.register("sw.js").catch(() => {}); } catch (e) {}
});

export { applyTheme, currentSongId, currentTemplatePath, ensureOcarinaTemplate };
window.applyTheme = applyTheme; window.currentSongId = currentSongId;
window.currentSongTitle = currentSongTitle; window.loadText = loadText;
window.switchInstrument = switchInstrument; window.installFingerings = installFingerings;
window.fillInstrumentSelect = fillInstrumentSelect; window.boot = boot;
window.currentTemplatePath = currentTemplatePath;
window.ensureOcarinaTemplate = ensureOcarinaTemplate;
window.loadJson = loadJson;
