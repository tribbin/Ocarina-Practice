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
}

async function loadText(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error("Could not load " + path + " (" + res.status + ")");
  return res.text();
}

async function loadJson(path) {
  return JSON.parse(await loadText(path));
}

async function boot() {
  try {
    const [fing, songs, svgText, cssText] = await Promise.all([
      loadJson("fingerings.json"),
      loadJson("songs.json"),
      loadText("ocarina-template.svg"),
      loadText("css/app.css")
    ]);
    APP_CSS = cssText;
    installFingerings(fing);
    installOcarinaTemplate(svgText);
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
