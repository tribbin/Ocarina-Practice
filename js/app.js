window.onerror = function(m, s, l) {
  const e = document.getElementById("err");
  if (e) e.textContent = m + " @" + l;
};

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

async function loadInstrument(inst) {
  const [fing, svgText] = await Promise.all([
    loadJson(inst.fingerings),
    loadText(inst.svg)
  ]);
  installFingerings(fing);
  installOcarinaTemplate(svgText);
  window.CURRENT_INSTRUMENT = inst;
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
  await loadInstrument(inst);
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
    const [manifest, songs, cssText] = await Promise.all([
      loadJson("instruments.json"),
      loadJson("songs.json"),
      loadText("css/app.css")
    ]);
    APP_CSS = cssText;
    window.INSTRUMENTS = manifest.instruments || [];
    const chosen = INSTRUMENTS.find(i => i.id === manifest.default) || INSTRUMENTS[0];
    if (!chosen) throw new Error("No instruments defined in instruments.json");
    await loadInstrument(chosen);
    fillInstrumentSelect(chosen.id);
    wireInstrumentPicker();
    initBuiltin(songs);
    wireLibrary();
    wireUi();
    fillLibrary("major");
    buildKB();
    loadLibraryItem("major");
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
