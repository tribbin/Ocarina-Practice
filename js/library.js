const LIB_KEY = "oco-bass-c-library";
const SHOW_HIDDEN_KEY = "oco-bass-c-show-hidden";
let BUILTIN = {};

function initBuiltin(songs) {
  BUILTIN = songs || {};
  if (BUILTIN.chromatic && !BUILTIN.chromatic.body) {
    BUILTIN.chromatic.body = NOTES.map(n => n.replace(/^([A-G])s/, "$1#")).join(" ");
  }
}

function userLib() {
  try { return JSON.parse(localStorage.getItem(LIB_KEY) || "{}") || {}; }
  catch (e) { return {}; }
}

function setUserLib(obj) {
  localStorage.setItem(LIB_KEY, JSON.stringify(obj));
}

function slugName(name) {
  return "u-" + String(name).trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || ("song-" + Date.now());
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

function setShowHidden(v) {
  localStorage.setItem(SHOW_HIDDEN_KEY, v ? "1" : "0");
}

function fillLibrary(selectId) {
  const sel = document.getElementById("scale");
  const cur = selectId !== undefined ? selectId : sel.value;
  sel.innerHTML = "";
  const groups = {};
  Object.keys(BUILTIN).forEach(id => {
    const item = BUILTIN[id];
    if (item.hidden && !showHiddenSongs()) return;
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
  const ids = Object.keys(user);
  if (ids.length) {
    const g2 = document.createElement("optgroup"); g2.label = "My songs";
    ids.forEach(id => {
      const o = document.createElement("option"); o.value = id; o.textContent = user[id].name || id; g2.appendChild(o);
    });
    sel.appendChild(g2);
  }
  if (cur && [...sel.options].some(o => o.value === cur)) sel.value = cur;
  else if (!cur) sel.selectedIndex = -1;
  syncLibraryMenu();
}

function clearLibrarySelection() {
  const sel = document.getElementById("scale");
  if (!sel || !sel.value) return;
  sel.selectedIndex = -1;
  syncLibraryMenu();
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

function syncLibraryMenu() {
  const sel = document.getElementById("scale");
  const menu = document.getElementById("libDdMenu");
  const text = document.getElementById("libDdText");
  if (!sel || !menu || !text) return;
  const cur = sel.value;
  const chosen = sel.options[sel.selectedIndex];
  text.textContent = chosen ? chosen.textContent : "";
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

function currentTempo() {
  const el = document.getElementById("tempo");
  return Math.max(40, Math.min(180, +(el && el.value) || 100));
}

function applyTempo(bpm) {
  bpm = Math.max(40, Math.min(180, +bpm || 100));
  const el = document.getElementById("tempo");
  const lab = document.getElementById("tempoVal");
  if (el) el.value = String(bpm);
  if (lab) lab.textContent = String(bpm);
  const fEl = document.getElementById("focusTempo");
  const fLab = document.getElementById("focusTempoVal");
  if (fEl) fEl.value = String(bpm);
  if (fLab) fLab.textContent = String(bpm);
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

function loadLibraryItem(id) {
  if (typeof stopMelody === "function") stopMelody();
  if (typeof resetLiveTab === "function") resetLiveTab();
  let tempo = currentTempo();
  let swing = currentSwing();
  if (BUILTIN[id]) {
    const item = BUILTIN[id];
    const body = String(item.body || "").replace(/^\s*#.*\n/, "");
    tempo = item.tempo || tempoFromText(item.body) || 96;
    swing = item.swing != null ? item.swing : (swingFromText(item.body) || 0);
    document.getElementById("src").value = withPlayHeaders(body.trim(), item.name, tempo, swing);
  } else {
    const item = userLib()[id];
    if (item) {
      document.getElementById("src").value = item.body || "";
      tempo = item.tempo || tempoFromText(item.body) || tempo;
      swing = item.swing != null ? item.swing : (swingFromText(item.body) != null ? swingFromText(item.body) : swing);
    }
  }
  applyTempo(tempo);
  applySwing(swing);
  render();
}

function wireLibrary() {
  wireLibraryDropdown();
  document.getElementById("scale").onchange = e => loadLibraryItem(e.target.value);
  document.getElementById("src").addEventListener("input", clearLibrarySelection);
  document.getElementById("libSave").onclick = () => {
    const ta = document.getElementById("src");
    const body = ta.value;
    const suggested = titleFromText(body);
    const name = prompt("Name in library:", suggested || "My song");
    if (!name || !name.trim()) return;
    const named = name.trim();
    const lib = userLib();
    const id = slugName(named);
    const tempo = currentTempo();
    const swing = currentSwing();
    const next = withPlayHeaders(body, named, tempo, swing);
    ta.value = next;
    lib[id] = { name: named, body: next, tempo, swing };
    setUserLib(lib);
    fillLibrary(id);
    render();
  };
  document.getElementById("libRemove").onclick = () => {
    const id = document.getElementById("scale").value;
    if (BUILTIN[id]) { alert("Built-in presets cannot be removed."); return; }
    const lib = userLib();
    if (!lib[id]) return;
    if (!confirm("Remove \"" + (lib[id].name || id) + "\" from this browser?")) return;
    delete lib[id];
    setUserLib(lib);
    fillLibrary("major");
    loadLibraryItem("major");
  };
  document.getElementById("diskSave").onclick = () => {
    const body = document.getElementById("src").value;
    const name = (titleFromText(body) || "melody").replace(/[^\w\- ]+/g, "").trim() || "melody";
    const blob = new Blob([withPlayHeaders(body, null, currentTempo(), currentSwing())], {type: "text/plain"});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name + ".txt";
    a.click();
    URL.revokeObjectURL(a.href);
  };
  document.getElementById("diskLoad").onclick = () => document.getElementById("diskFile").click();
  document.getElementById("diskFile").onchange = e => {
    const f = e.target.files && e.target.files[0];
    e.target.value = "";
    if (!f) return;
    const reader = new FileReader();
    reader.onload = () => {
      let text = String(reader.result || "");
      let tpo = null, sw = null;
      try {
        const j = JSON.parse(text);
        if (j && typeof j.body === "string") text = j.body;
        else if (j && typeof j.melody === "string") text = j.melody;
        if (j && j.tempo) tpo = j.tempo;
        if (j && j.swing != null) sw = j.swing;
      } catch (err) {}
      document.getElementById("src").value = text;
      tpo = tpo || tempoFromText(text);
      if (tpo) applyTempo(tpo);
      sw = sw != null ? sw : swingFromText(text);
      if (sw != null) applySwing(sw);
      clearLibrarySelection();
      render();
    };
    reader.readAsText(f);
  };
}
