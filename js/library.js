import { isOutOfRange, parse, swingFromText, tempoFromText, titleFromText,
         withPlayHeaders } from "./parse.js";
import { stopMelody } from "./audio.js";
import { render, resetLiveTab } from "./ui.js";
import { practiceInvalidate } from "./practice.js";
import { ensureOcarinaTemplate } from "./app.js";
const LIB_KEY = "oco-bass-c-library";
const SHOW_HIDDEN_KEY = "oco-bass-c-show-hidden";
let BUILTIN = {};

function initBuiltin(songs) {
  BUILTIN = songs || {};
  window.BUILTIN = BUILTIN; // compat mirror (shipped-songs probes read it)
}

const DISPLAY_ID = i => i.replace(/^([A-G])s/, "$1#");
const BLACK_KEY = i => /^([A-G])s/.test(i);

// The C-major and chromatic entries are TOOLS, not content: the library
// synthesizes them for the LOADED chart and regenerates on every instrument
// install, so they can never be out of range or drift from the fingerings
// (nothing of them ships in songs.json).
function refreshGeneratedScales(chartIds) {
  const ids = Array.isArray(chartIds) ? chartIds : [];
  BUILTIN.chromatic = {
    name: "Chromatic", group: "Scales", tempo: 120,
    body: ids.map(DISPLAY_ID).join(" "),
  };
  BUILTIN.major = {
    name: "C major", group: "Scales", tempo: 120,
    body: ids.filter(i => !BLACK_KEY(i)).map(DISPLAY_ID).join(" "),
  };
  window.BUILTIN = BUILTIN;
}

function userLib() {
  let raw = null;
  try { raw = localStorage.getItem(LIB_KEY); } catch (e) { raw = null; }
  if (!raw) return {};
  let parsed = null;
  try { parsed = JSON.parse(raw); } catch (e) { parsed = null; }
  if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) return parsed;
  // Corrupt or non-object content: keep the evidence (backed up once) and
  // reset the key so the next real save isn't reading from a poisoned value —
  // otherwise a save would silently overwrite the broken state and the data
  // is lost for good.
  try {
    localStorage.setItem(LIB_KEY + ".corrupt-" + Date.now(), raw);
    localStorage.setItem(LIB_KEY, "{}");
  } catch (e) {}
  return {};
}

// Returns true when the write landed; false means storage refused it (quota
// exceeded, private mode…) and callers must surface that instead of letting
// the save quietly do nothing.
function setUserLib(obj) {
  try { localStorage.setItem(LIB_KEY, JSON.stringify(obj)); return true; }
  catch (e) { return false; }
}

function slugName(name) {
  // Punctuation-only or junk names slugify to "" and would all share one id
  // ("u-"); give those a timestamped id instead.
  const base = String(name).trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return base ? "u-" + base : "song-" + Date.now();
}

// Re-saving the exact same display name is a deliberate overwrite; any other
// id collision (e.g. punctuation-differing names that slugify identically)
// gets a -2, -3, … suffix instead of silently replacing the stored song.
function uniqueUserId(lib, name) {
  const base = slugName(name);
  let id = base;
  let n = 1;
  while (lib[id] && lib[id].name !== name) id = base + "-" + (++n);
  return id;
}

// Full melody text for a library id (built-in or user), or "" if unknown.
function songBody(id) {
  if (BUILTIN[id]) return String(BUILTIN[id].body || "");
  const item = userLib()[id];
  return item ? String(item.body || "") : "";
}

// How many notes in a song fall outside the current ocarina's range.
function songOutOfRange(id) {
  if (typeof parse !== "function" || typeof isOutOfRange !== "function") return 0;
  let n = 0;
  for (const t of parse(songBody(id))) {
    if ((t.type === "note" || t.type === "tie") && t.id && isOutOfRange(t.id)) n++;
  }
  return n;
}

// Songs flagged hidden that are currently revealed via the library menu toggle.
function showHiddenSongs() {
  return localStorage.getItem(SHOW_HIDDEN_KEY) === "1";
}

// Playable-on-chart fit for the instrument-switch song jump: every melody
// token id must be ON the loaded chart — stricter than songOutOfRange's
// out-of-compass count, which lets a between-lows-and-highs id the chart
// never exposes (a black key on a all-white-key body) count as in range.
function songFitsChart(id) {
  const item = BUILTIN[id];
  if (!item || !Array.isArray(window.NOTES) || !window.NOTES.length) return false;
  for (const t of parse(String(item.body || ""))) {
    if ((t.type === "note" || t.type === "tie") && t.id &&
        !window.NOTES.includes(t.id)) return false;
  }
  return true;
}

// The library song currently in the editor, even when the range filter keeps
// it out of the dropdown (#scale silently unselects — the ?song deep link
// must keep loading it). loadLibraryItem is the only writer; the exact
// editor-content contract ends where clearLibrarySelection fires (typed
// text, note clicks, Clear, file load), and the tracker goes with it.
let lastLoadedId = "";
function loadedLibraryId() { return lastLoadedId; }

function setShowHidden(v) {
  try { localStorage.setItem(SHOW_HIDDEN_KEY, v ? "1" : "0"); } catch (e) {}
}

// Robin's dropdown order for the generated scales (the IDEAS lift): the
// whole Scales group opens the list — the beginner's tool set first — and
// inside it C major (the chart minus black keys) comes before Chromatic,
// regardless of the order the synthesizer happened to assign its keys.
const SCALE_ORDER = ["major", "chromatic"];

function fillLibrary(selectId) {
  const sel = document.getElementById("scale");
  const cur = selectId !== undefined ? selectId : sel.value;
  sel.innerHTML = "";
  const showHidden = showHiddenSongs();
  // Songs are hidden when statically flagged OR when they contain notes
  // outside the currently selected ocarina's range; both kinds are revealed
  // by the same "Show hidden songs" toggle.
  const live = Object.keys(BUILTIN).filter(id => {
    const item = BUILTIN[id];
    return !((item.hidden || songOutOfRange(id) > 0) && !showHidden);
  });
  const scaleRank = id => {
    const r = SCALE_ORDER.indexOf(id);
    return r < 0 ? SCALE_ORDER.length : r;
  };
  const isScale = id => BUILTIN[id].group === "Scales";
  const scaleIds = live.filter(isScale)
    .map((id, ix) => ({ id, ix }))
    .sort((a, b) => scaleRank(a.id) - scaleRank(b.id) || a.ix - b.ix)
    .map(o => o.id);
  const ordered = [...scaleIds, ...live.filter(id => !isScale(id))];
  const groups = {};
  ordered.forEach(id => {
    const item = BUILTIN[id];
    if ((item.hidden || songOutOfRange(id) > 0) && !showHidden) return;
    const gname = item.group || "Built-in";
    if (!groups[gname]) {
      groups[gname] = document.createElement("optgroup");
      groups[gname].label = gname;
      sel.appendChild(groups[gname]);
    }
    const o = document.createElement("option");
    o.value = id;
    o.textContent = item.hidden ? (item.name || id) + " (hidden)" : (item.name || id);
    groups[gname].appendChild(o);
  });
  const user = userLib();
  const ids = Object.keys(user).filter(id => showHidden || songOutOfRange(id) === 0);
  if (ids.length) {
    const g2 = document.createElement("optgroup"); g2.label = "My songs";
    ids.forEach(id => {
      const o = document.createElement("option"); o.value = id; o.textContent = user[id].name || id; g2.appendChild(o);
    });
    sel.appendChild(g2);
  }
  // Keep the selection if it survived the filter; otherwise drop it so the
  // dropdown cannot keep pointing at a song that is currently hidden.
  if (cur && [...sel.options].some(o => o.value === cur)) sel.value = cur;
  else sel.selectedIndex = -1;
  syncLibraryMenu(cur);
}

// -------------------------------------------------- landed-crawler URLs
// Robin, IDEAS 2026-09-25: a /song/… landing page IS that song's clean
// canonical path (the stub's seed keeps it), but any LATER content change —
// a library load, a loader-less song swap, a typed replacement — must never
// sit under some other song's deep path. The URL then resolves to the SITE
// ROOT with the ? GET vars (root + ?song=<key>&inst=<inst>, or bare root
// when nothing library-identifiable is loaded). Mount-agnostic by
// construction: the root is the current pathname minus its /song/ tail, so
// both a domain-root and a project-page mount land on their own root.
// Once the session HAS left a deep path, the ?song= var must keep tracking
// the playing song: a later library load lands on the root where the stub
// matcher is empty, and the vars refresh in place (extras such as theme
// params survive; only song= and inst= are rewritten).
// markUrlLanded() gates the rewrites: the boot's own deep-link load may
// only ever KEEP the landing path — the brain of the seed.
let urlLanded = false;
function markUrlLanded() { urlLanded = true; }
const STUB_PATH = /^(.*\/)?song\/[^/]+\/[^/]+\/$/;
function rewriteLanderUrl() {
  if (!urlLanded) return;
  const m = location.pathname.match(STUB_PATH);
  const root = m ? (m[1] || "/") : location.pathname;
  const sel = document.getElementById("scale");
  const song = (sel && sel.value) || lastLoadedId || "";
  const pick = document.getElementById("instSel");
  const inst = (pick && pick.value) || "";
  let q = new URLSearchParams(location.search);
  q.delete("song");
  q.delete("inst");
  if (song) q.set("song", song);
  if (inst) q.set("inst", inst);
  q = "?" + q.toString();
  if (q === "?") q = "";
  const next = root + q;
  if (next !== location.pathname + location.search)
    history.replaceState(null, "", next);
}

function clearLibrarySelection() {
  // The exact-library-body contract ends here (typed text, note clicks,
  // Clear, file load) — the hidden-song tracker must clear even when the
  // dropdown selection is already empty (the guarded branch below).
  lastLoadedId = "";
  const sel = document.getElementById("scale");
  if (sel && sel.value) {
    sel.selectedIndex = -1;
    syncLibraryMenu();
  }
  // Typed/cleared/file-loaded content is a different song than the one
  // the landing path names: the URL leaves the deep path once boot is
  // behind us — and only AFTER the selection dropped, so a rewrite never
  // names the replaced song (no library key remains → bare root).
  // Idempotent: on the root the path matcher is already empty.
  try { rewriteLanderUrl(); } catch (e) {}
}

function libraryMenuOpen() {
  const menu = document.getElementById("libDdMenu");
  return menu && !menu.hidden;
}

function closeLibraryMenu() {
  const menu = document.getElementById("libDdMenu");
  const btn = document.getElementById("libDdBtn");
  if (!menu || menu.hidden) return;
  menu.hidden = true;
  if (btn) btn.setAttribute("aria-expanded", "false");
}

function openLibraryMenu() {
  const menu = document.getElementById("libDdMenu");
  const btn = document.getElementById("libDdBtn");
  if (!menu) return;
  syncLibraryMenu();
  menu.hidden = false;
  if (btn) btn.setAttribute("aria-expanded", "true");
  const selected = menu.querySelector('.lib-dd-opt[aria-selected="true"]') || menu.querySelector(".lib-dd-opt");
  if (selected) selected.focus();
}

function toggleLibraryMenu() {
  if (libraryMenuOpen()) closeLibraryMenu();
  else openLibraryMenu();
}

function pickLibrary(id) {
  const sel = document.getElementById("scale");
  const changed = sel && sel.value !== id;
  closeLibraryMenu();
  if (changed) {
    sel.value = id;
    sel.dispatchEvent(new Event("change"));
  }
  syncLibraryMenu();
}

function syncLibraryMenu(holdId) {
  const sel = document.getElementById("scale");
  const menu = document.getElementById("libDdMenu");
  const text = document.getElementById("libDdText");
  if (!sel || !menu || !text) return;
  const cur = sel.value;
  const chosen = sel.options[sel.selectedIndex];
  let label = chosen ? chosen.textContent : "";
  // A song can drop out of the filtered list (out of range / hidden) while
  // still being the song loaded in the editor: the label must keep saying so
  // instead of collapsing flat. Genuinely different content (Clear / typed)
  // shows the placeholder.
  if (!label && holdId) {
    const item = BUILTIN[holdId]
      || (typeof userLib === "function" ? userLib()[holdId] : null);
    if (item) label = item.name || holdId;
  }
  text.textContent = label || "No song selected";
  text.classList.toggle("placeholder", !label);
  menu.innerHTML = "";
  for (const node of sel.children) {
    if (node.tagName === "OPTGROUP") {
      const g = document.createElement("div");
      g.className = "lib-dd-group";
      g.textContent = node.label;
      menu.appendChild(g);
      for (const opt of node.children) menu.appendChild(libraryOptionEl(opt, cur));
    } else if (node.tagName === "OPTION") {
      menu.appendChild(libraryOptionEl(node, cur));
    }
  }
  const foot = document.createElement("div");
  foot.className = "lib-dd-foot";
  const cb = document.createElement("input");
  cb.type = "checkbox";
  cb.checked = showHiddenSongs();
  cb.addEventListener("change", () => {
    setShowHidden(cb.checked);
    fillLibrary(sel.value);
    const again = document.getElementById("libDdMenu");
    if (again && !again.hidden) {
      const f = again.querySelector(".lib-dd-foot input");
      if (f) f.focus();
    }
  });
  const lab = document.createElement("label");
  lab.appendChild(cb);
  lab.appendChild(document.createTextNode(" Show hidden songs"));
  foot.appendChild(lab);
  menu.appendChild(foot);
}

function libraryOptionEl(opt, cur) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = "lib-dd-opt";
  b.setAttribute("role", "option");
  b.dataset.value = opt.value;
  const name = document.createElement("span");
  name.className = "lib-dd-name";
  name.textContent = opt.textContent;
  b.appendChild(name);
  const oor = songOutOfRange(opt.value);
  if (oor > 0) {
    b.classList.add("has-oor");
    const badge = document.createElement("span");
    badge.className = "lib-dd-oor";
    badge.textContent = "\u26A0 " + oor;
    badge.setAttribute("aria-hidden", "true");
    b.appendChild(badge);
    const noun = oor === 1 ? "note" : "notes";
    b.title = oor + " " + noun + " out of range for this ocarina";
    b.setAttribute("aria-label", opt.textContent + " — " + oor + " " + noun + " out of range");
  }
  if (opt.value === cur) b.setAttribute("aria-selected", "true");
  b.addEventListener("click", e => {
    e.preventDefault();
    e.stopPropagation();
    pickLibrary(opt.value);
    const btn = document.getElementById("libDdBtn");
    if (btn) btn.focus();
  });
  return b;
}

function libraryOptions() {
  return [...document.querySelectorAll("#libDdMenu .lib-dd-opt")];
}

function wireLibraryDropdown() {
  const wrap = document.getElementById("libDd");
  const btn = document.getElementById("libDdBtn");
  if (!wrap || !btn) return;
  btn.addEventListener("click", e => {
    e.preventDefault();
    e.stopPropagation();
    toggleLibraryMenu();
  });
  document.addEventListener("pointerdown", e => {
    if (!wrap.contains(e.target)) closeLibraryMenu();
  });
  document.addEventListener("keydown", e => {
    if (!libraryMenuOpen()) return;
    if (e.key === "Escape") {
      e.preventDefault();
      closeLibraryMenu();
      btn.focus();
      return;
    }
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp" && e.key !== "Home" && e.key !== "End") return;
    e.preventDefault();
    const opts = libraryOptions();
    if (!opts.length) return;
    const i = opts.indexOf(document.activeElement);
    let n = 0;
    if (e.key === "ArrowDown") n = i < 0 ? 0 : (i + 1) % opts.length;
    else if (e.key === "ArrowUp") n = i < 0 ? opts.length - 1 : (i - 1 + opts.length) % opts.length;
    else if (e.key === "End") n = opts.length - 1;
    opts[n].focus();
  });
}

// The tempo slider is a RELATIVE playback speed (10–100%) applied on top of
// the song's own tempo (its leading "# tempo" header and any inline "# tempo"
// changes), never an absolute BPM.
function tempoPct() {
  const el = document.getElementById("tempo");
  return Math.max(10, Math.min(100, (el ? +el.value : 100) || 100));
}

// The song's own base tempo comes from its text (leading "# tempo" header),
// defaulting to 100 — used for library metadata/headers only.
function songTempo() {
  const ta = document.getElementById("src");
  return Math.max(10, Math.min(400,
    (ta && (tempoFromText(ta.value) || 100)) || 100));
}

function applyTempoPct(pct) {
  pct = String(Math.max(10, Math.min(100, Math.round(+pct || 100))));
  const el = document.getElementById("tempo");
  const lab = document.getElementById("tempoVal");
  if (el) el.value = pct;
  if (lab) lab.textContent = pct;
  const fEl = document.getElementById("focusTempo");
  const fLab = document.getElementById("focusTempoVal");
  if (fEl) fEl.value = pct;
  if (fLab) fLab.textContent = pct;
}

function currentSwing() {
  const el = document.getElementById("swing");
  return Math.max(0, Math.min(100, +(el && el.value) || 0));
}

function applySwing(n) {
  n = Math.max(0, Math.min(100, +n || 0));
  const el = document.getElementById("swing");
  const lab = document.getElementById("swingVal");
  if (el) el.value = String(n);
  if (lab) lab.textContent = String(n);
}

// Optional per-song playback defaults live as JSON fields next to
// name/tempo/swing (e.g. "tick": false starts the metronome switched off).
// Only applied when the song actually specifies one; otherwise the user's
// current checkbox state carries over.
function applySongTick(v) {
  if (v == null) return;
  const cb = document.getElementById("tickMel");
  if (cb) {
    cb.checked = !!v;
    cb.dispatchEvent(new Event("change")); // the tick button mirrors the carrier
  }
}

function loadLibraryItem(id) {
  if (typeof stopMelody === "function") stopMelody();
  if (typeof resetLiveTab === "function") resetLiveTab();
  // A different song invalidates any practice session (see practiceInvalidate
  // in js/practice.js): stop it so the next Practice press starts fresh on
  // this song rather than resuming the replaced song's stale tuner targets.
  if (typeof practiceInvalidate === "function") try { practiceInvalidate(); } catch (e) {}
  // The song's tempo lives in its text (withPlayHeaders writes the header);
  // the relative playback speed stays at the user's dial between songs.
  let tempo = 100;
  let swing = currentSwing();
  let tick;
  let loadedId = "";
  if (BUILTIN[id]) {
    const item = BUILTIN[id];
    const body = String(item.body || "").replace(/^\s*#.*\n/, "");
    tempo = item.tempo || tempoFromText(item.body) || 96;
    swing = item.swing != null ? item.swing : (swingFromText(item.body) || 0);
    tick = item.tick;
    document.getElementById("src").value = withPlayHeaders(body.trim(), item.name, tempo, swing);
    loadedId = id;
  } else {
    const item = userLib()[id];
    if (item) {
      document.getElementById("src").value = item.body || "";
      tempo = item.tempo || tempoFromText(item.body) || tempo;
      swing = item.swing != null ? item.swing : (swingFromText(item.body) != null ? swingFromText(item.body) : swing);
      tick = item.tick;
      loadedId = id;
    }
  }
  // Only traffic that actually loaded a body counts; an onchange with a
  // missing id leaves the editor (and the tracker) as they were.
  if (loadedId) lastLoadedId = loadedId;
  // A landed-crawler switch leaves the deep path (root + ?song=&inst=);
  // boot's own loads arrive pre-mark and keep their landing path.
  try { rewriteLanderUrl(); } catch (e) {}
  applySwing(swing);
  applySongTick(tick);
  if (typeof ensureOcarinaTemplate === "function") {
    ensureOcarinaTemplate().then(() => render());
  } else {
    render();
  }
}

// Small non-blocking notice pill (fixed bottom, auto-fades). Used to explain
// library states that would otherwise look like a no-op (e.g. a freshly
// saved song being filed as hidden by the range rule).
let libToastEl = null, libToastTimer = 0;
function libToast(msg) {
  if (typeof document === "undefined") return;
  if (libToastTimer) { clearTimeout(libToastTimer); libToastTimer = 0; }
  if (!libToastEl) {
    libToastEl = document.createElement("div");
    libToastEl.className = "lib-toast noprint";
    document.body.appendChild(libToastEl);
  }
  libToastEl.textContent = msg
  libToastEl.hidden = false;
  libToastTimer = setTimeout(() => { if (libToastEl) libToastEl.hidden = true; }, 6500);
}

// alert() / prompt() / confirm() throw inside sandboxed and embedded views
// ("prompt() is not supported"), which made the library buttons unusable
// there. In-page equivalents for everything modal.
function safeAlert(msg) {
  try { alert(msg); } catch (e) { libToast(msg); }
}
// One dialog core for both shapes: libPrompt carries an input and resolves
// null on cancel OR empty submit (exactly like the native prompt() it
// replaced), libConfirm resolves true/false on Enter/Escape/buttons.
function libModal(opts) {
  return new Promise(resolve => {
    if (typeof document === "undefined") { resolve(opts.input ? null : false); return; }
    const wrap = document.createElement("div");
    wrap.className = "lib-dialog noprint";
    wrap.innerHTML =
      '<div class="lib-dialog-card">' +
      '<div class="lib-dialog-title"></div>' +
      (opts.input ? '<input type="text" class="lib-dialog-input" spellcheck="false" maxlength="80">' : "") +
      '<div class="lib-dialog-row">' +
      '<button type="button" class="lib-dialog-ok">' + opts.okLabel + '</button>' +
      '<button type="button" class="lib-dialog-cancel">' + opts.cancelLabel + '</button></div></div>';
    wrap.querySelector(".lib-dialog-title").textContent = opts.text;
    const input = opts.input ? wrap.querySelector("input") : null;
    if (input) input.value = opts.suggested || "";
    document.body.appendChild(wrap);
    let closed = false;
    const finishing = (val) => {
      if (closed) return;
      closed = true;
      wrap.remove();
      document.removeEventListener("keydown", key);
      if (input) {
        const name = (val || "").trim();
        resolve(name || null);       // empty means cancel, like prompt() did
      } else {
        resolve(val);
      }
    };
    const key = (e) => {
      if (e.key === "Enter") { e.preventDefault(); finishing(input ? input.value : true); }
      else if (e.key === "Escape") { e.preventDefault(); finishing(input ? null : false); }
    };
    wrap.querySelector(".lib-dialog-ok").addEventListener("click", () => finishing(input ? input.value : true));
    wrap.querySelector(".lib-dialog-cancel").addEventListener("click", () => finishing(input ? null : false));
    document.addEventListener("keydown", key);
    if (input) setTimeout(() => { try { input.focus(); input.select(); } catch (e) {} }, 0);
  });
}
function libPrompt(title, suggested) {
  return libModal({ input: true, text: title, okLabel: "Save", cancelLabel: "Cancel", suggested });
}
function libConfirm(text) {
  return libModal({ text, okLabel: "Remove", cancelLabel: "Cancel" });
}

function wireLibrary() {
  wireLibraryDropdown();
  document.getElementById("scale").onchange = e => loadLibraryItem(e.target.value);
  document.getElementById("src").addEventListener("input", clearLibrarySelection);
  document.getElementById("libSave").onclick = async () => {
    const ta = document.getElementById("src");
    const body = ta.value;
    const suggested = titleFromText(body);
    const name = await libPrompt("Name in library:", suggested || "My song");
    if (!name) return;
    const named = name;
    const lib = userLib();
    const id = uniqueUserId(lib, named);
    const tempo = songTempo();
    const swing = currentSwing();
    const tickEl = document.getElementById("tickMel");
    const next = withPlayHeaders(body, named, tempo, swing);
    ta.value = next;
    lib[id] = { name: named, body: next, tempo, swing, tick: tickEl ? tickEl.checked : undefined };
    const saved = setUserLib(lib);
    if (!saved) {
      // The text (possibly with the added headers) stays in the editor, so
      // nothing is lost — only the library filing refused.
      libToast("Could not save to the library — browser storage is full or blocked.");
      render();
      return;
    }
    fillLibrary(id);
    render();
    // The range rule may file the song as hidden for THIS ocarina: say so,
    // otherwise saving looks like a no-op.
    if (!showHiddenSongs() && songOutOfRange(id) > 0) {
      const n = songOutOfRange(id);
      libToast("\"" + named + "\" saved — filed as hidden: " + n +
        " note" + (n === 1 ? "" : "s") + " outside this ocarina's range. " +
        "Tick \"Show hidden songs\" in the library to see it.");
    }
  };
  document.getElementById("libRemove").onclick = async () => {
    const id = document.getElementById("scale").value;
    if (BUILTIN[id]) { safeAlert("Built-in presets cannot be removed."); return; }
    const lib = userLib();
    if (!lib[id]) return;
    if (!(await libConfirm("Remove \"" + (lib[id].name || id) + "\" from this browser?"))) return;
    delete lib[id];
    if (!setUserLib(lib)) {
      libToast("Could not remove — browser storage is full or blocked.");
      return;
    }
    fillLibrary("major");
    loadLibraryItem("major");
  };
  document.getElementById("diskSave").onclick = () => {
    const body = document.getElementById("src").value;
    const name = (titleFromText(body) || "melody").replace(/[^\w\- ]+/g, "").trim() || "melody";
    const blob = new Blob([withPlayHeaders(body, null, songTempo(), currentSwing())], {type: "text/plain"});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name + ".txt";
    a.click();
    // Defer the revoke (drain later): revoking in the same tick as the click
    // historically aborts the download in some engines (blob mapping torn
    // down before the downloader attaches). Same pattern as debug.js export.
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  };
  document.getElementById("diskLoad").onclick = () => document.getElementById("diskFile").click();
  document.getElementById("diskFile").onchange = e => {
    const f = e.target.files && e.target.files[0];
    e.target.value = "";
    if (!f) return;
    const reader = new FileReader();
    reader.onload = () => {
      let text = String(reader.result || "");
      let sw = null;
      try {
        const j = JSON.parse(text);
        if (j && typeof j.body === "string") text = j.body;
        else if (j && typeof j.melody === "string") text = j.melody;
        if (j && j.swing != null) sw = j.swing;
      } catch (err) {}
      document.getElementById("src").value = text;
      sw = sw != null ? sw : swingFromText(text);
      if (sw != null) applySwing(sw);
      clearLibrarySelection();
      // The loaded file replaces the melody: a parked/running practice
      // session belongs to the previous song (see practiceInvalidate).
      if (typeof practiceInvalidate === "function") try { practiceInvalidate(); } catch (e) {}
      render();
    };
    reader.readAsText(f);
  };
}

export { BUILTIN, applySwing, applyTempoPct, clearLibrarySelection, currentSwing,
         fillLibrary, initBuiltin, libToast, loadedLibraryId, loadLibraryItem,
         markUrlLanded, rewriteLanderUrl, safeAlert, songFitsChart,
         songTempo,
         syncLibraryMenu, tempoPct, userLib, wireLibrary, setUserLib, slugName,
         uniqueUserId, showHiddenSongs, refreshGeneratedScales };

// Classic-script compat surface (tests + dev console).
window.userLib = userLib; window.setUserLib = setUserLib; window.slugName = slugName;
window.uniqueUserId = uniqueUserId; window.withPlayHeaders = withPlayHeaders;
window.fillLibrary = fillLibrary; window.initBuiltin = initBuiltin;
window.loadLibraryItem = loadLibraryItem; window.tempoFromText = tempoFromText;
window.markUrlLanded = markUrlLanded; window.rewriteLanderUrl = rewriteLanderUrl;
window.applySongTick = applySongTick;
window.setShowHidden = setShowHidden;
window.showHiddenSongs = showHiddenSongs;
