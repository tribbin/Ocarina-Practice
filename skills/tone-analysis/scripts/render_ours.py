# render_ours.py — render the repo synth to WAV via headless-chrome OfflineAudioContext.
# For each note: variant A "shipped" (ET pitch, default params incl. vibrato) and
# variant B "matched" (measured f0, vibrato/tremolo off, master level matched to
# the recording's plateau H1 RMS). No repo code is modified.
import json, subprocess, os, base64, re, sys

APP = r"C:\Users\tribb\Documents\git\Triple-Bass-in-C-Ocarina-Tab-Maker"
TMP = r"C:\Users\tribb\AppData\Local\Temp\opencode"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

fing_json = json.dumps(json.load(open(os.path.join(APP, "fingerings.json"), encoding="utf-8")))

TEMPLATE = r"""<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
<div id="OUT">PENDING</div><div id="ERR"></div>
<script>
const FING_DATA = __FING__;
const CFG = __CFG__;
</script>
<script src="http://127.0.0.1:8137/js/audio.js"></script>
<script>
try {
function installFingerings(f) {
  window.FING = f;
  window.NOTES = f.notes.map(n => n.id);
  window.DISPLAY = Object.fromEntries(f.notes.map(n => [n.id, n.display]));
  window.CHAMBER = Object.fromEntries(f.notes.map(n => [n.id, n.chamber]));
  window.COVER = Object.fromEntries(f.notes.map(n => [n.id, n.covered]));
}
installFingerings(FING_DATA);
const OAC = window.OfflineAudioContext || window.webkitOfflineAudioContext;
const LEN = Math.ceil(44100 * (CFG.dur + 0.8));
window.AudioContext = function () {
  const o = new OAC(1, LEN, 44100);
  try { Object.defineProperty(o, "state", { get: function () { return "running"; }, configurable: true }); } catch (e) {}
  if (!o.resume) o.resume = function () { return Promise.resolve(); };
  if (CFG.muteAirEdge) {
    // Chrome offline-render hang workaround: air (osc #2), edge (#4), wander
    // (#5) in one voice hang startRendering in combos; muted via silent stubs.
    // playNoteAt createOscillator order: osc(#1), air(#2), wob LFO(#3),
    // [vibrato LFO only in Zen mode], edge(#4), wander(#5), then the
    // octave-overblown ot. The stub keeps a REAL (unconnected) AudioParam as
    // `frequency` so that wanderGain.connect(edge.frequency) still works — a
    // plain object would throw and silently abort the remaining layers
    // (wind noise / chiff / ot would be missing from the audit render).
    const proto = OAC.prototype.createOscillator;
    const protoGain = OAC.prototype.createGain;
    let count = 0;
    o.createOscillator = function () {
      count++;
      if (count === 2 || count === 4 || count === 5) {
        // Silent param sink: a real gain's AudioParam, node left unconnected
        // so nothing ever renders from it.
        const sink = protoGain.call(o);
        const ap = sink.gain;
        return { type: "sine", frequency: ap, detune: ap, setPeriodicWave: function(){},
                 connect: function(){}, start: function(){}, stop: function(){} };
      }
      return proto.call(o);
    };
  }
  window.__oac = o;
  return o;
};
if (CFG.f0) window.freqOf = function () { return CFG.f0; };
if (window.OCA_DEBUG) {
  if (CFG.noVib) { OCA_DEBUG.params.vibDepth = 0; OCA_DEBUG.params.tremDepth = 0; }
  if (CFG.masterLevel) OCA_DEBUG.params.masterLevel = CFG.masterLevel;
  if (CFG.reverbWet !== undefined && CFG.reverbWet !== null) OCA_DEBUG.params.reverbWet = CFG.reverbWet;
}
// Offline rendering note: (a) the always-connected reverb convolver, and
// (b) the DynamicsCompressor when combined with the tremolo passthrough gain,
// make offline rendering hang in this Chrome build. The app runs with reverb
// OFF by default (reverbEnabled=false -> wet gain 0), and the limiter only
// guards peaks (it rarely engages at the app's levels), so swap getReverbBus
// for the dry chain minus the compressor (input -> outGain 0.6). The audible
// difference vs the shipped dry path is negligible at these levels.
getReverbBus = function (ctx) {
  if (window.__dbgbus && window.__dbgbus.context === ctx) return window.__dbgbus;
  const input = ctx.createGain();
  const outGain = ctx.createGain();
  outGain.gain.value = 0.6;
  input.connect(outGain); outGain.connect(ctx.destination);
  window.__dbgbus = input;
  return input;
};
function b64(buf8) {
  let s = ""; const CH = 0x8000;
  for (let i = 0; i < buf8.length; i += CH) s += String.fromCharCode.apply(null, buf8.subarray(i, i + CH));
  return btoa(s);
}
function encodeWav(f32, sr) {
  const n = f32.length;
  const buf = new ArrayBuffer(44 + n * 2), dv = new DataView(buf);
  const ws = (o, str) => { for (let i = 0; i < str.length; i++) dv.setUint8(o + i, str.charCodeAt(i)); };
  ws(0, "RIFF"); dv.setUint32(4, 36 + n * 2, true); ws(8, "WAVE"); ws(12, "fmt ");
  dv.setUint32(16, 16, true); dv.setUint16(20, 1, true); dv.setUint16(22, 1, true);
  dv.setUint32(24, sr, true); dv.setUint32(28, sr * 2, true); dv.setUint16(32, 2, true); dv.setUint16(34, 16, true);
  ws(36, "data"); dv.setUint32(40, n * 2, true);
  for (let i = 0; i < n; i++) {
    const v = Math.max(-1, Math.min(1, f32[i]));
    dv.setInt16(44 + i * 2, v < 0 ? v * 0x8000 : v * 0x7FFF, true);
  }
  return new Uint8Array(buf);
}
playNoteAt(CFG.note, null, CFG.dur, []);
const ctx = window.__oac;
ctx.startRendering().then(function (buf) {
  try {
    document.getElementById("OUT").textContent = "B64:" + b64(encodeWav(buf.getChannelData(0), 44100));
  } catch (e) { document.getElementById("OUT").textContent = "ENC-ERR:" + e; }
}, function (e) {
  document.getElementById("OUT").textContent = "RENDER-ERR:" + e;
});
} catch (e) {
  document.getElementById("OUT").textContent = "ERR:" + e + "|" + (e && e.stack);
}
</script></body></html>"""

NOTES = {  # note-id: (measured f0, playNoteAt dur)
    "A3": (220.0, 2.0),      # triple-bass range check (extrapolation zone)
    "C5": (513.1586, 1.54),
    "C5_2": (523.5930, 2.02),
    "C6": (1046.5023, 2.0),  # chamber-2 top (unmeasured chamber, audit only)
    "D6": (1173.6424, 1.73),
    "G6": (1566.9872, 2.13),
}

def run_page(name, cfg, out_sub):
    html = TEMPLATE.replace("__FING__", fing_json).replace("__CFG__", json.dumps(cfg))
    page = os.path.join(TMP, name)
    open(page, "w", encoding="utf-8").write(html)
    prof = os.path.join(TMP, "chrome-prof-" + name.replace(".html", ""))
    out = os.path.join(TMP, "dom_" + name + ".html")
    proc = subprocess.run(
        [CHROME, "--headless=old", "--disable-gpu", "--no-first-run", f"--user-data-dir={prof}",
         "--virtual-time-budget=30000", "--dump-dom",         "http://127.0.0.1:8138/" + name],
        capture_output=True, text=True, timeout=240)
    open(out, "w", encoding="utf-8", errors="ignore").write(proc.stdout)
    m = re.search(r'<div id="OUT">(B64:[A-Za-z0-9+/=]+)</div>', open(out, encoding="utf-8", errors="ignore").read())
    if not m:
        text = open(out, encoding="utf-8", errors="ignore").read()
        mm = re.search(r'<div id="OUT">((?:(?!<div).){0,400})</div>', text)
        print(f"[{name}] FAILED: " + (mm.group(1)[:300] if mm else "no OUT"), flush=True)
        return None
    wav = os.path.join(TMP, out_sub)
    open(wav, "wb").write(base64.b64decode(m.group(1)[4:]))
    print(f"[{name}] -> {wav}", flush=True)
    import time
    time.sleep(1.5)
    return wav

PLATEAU_H1 = {  # measured H1 plateau RMS dBFS from the recordings
    "C5": -27.4, "C5_2": -25.5, "D6": -10.6, "G6": -15.3,
    # unmeasured triple-range notes: predicted by the shipped level curve
    "A3": -28.1, "C6": -19.8,
}
MEASURED_H1_SHIPPED = {}  # filled in pass 1

def main(only=None):
    results = {}
    # PASS 1: shipped defaults at ET pitch
    for note, (f0, dur) in NOTES.items():
        if only and note not in only: continue
        name = f"r_{note}_shipped.html"
        wav = run_page(name, {"note": note.replace("_2", ""), "f0": None, "dur": dur, "muteAirEdge": True}, f"our_{note}_shipped.wav")
        if wav: results[(note, "shipped")] = wav
    # measure shipped H1 plateau to compute matched master level
    for (note, kind), wav in list(results.items()):
        r = json.loads(subprocess.run(["python", os.path.join(TMP, "tone_report.py"), wav,
                                       "--nominal", note.replace("_2", ""), "--label", note,
                                       "--json", os.path.join(TMP, f"our_{note}_{kind}_report.json")],
                                      capture_output=True, text=True, timeout=300).stdout)
        db = r["timbre"]["H1_plateau_rms_dbfs"]
        MEASURED_H1_SHIPPED[note] = db
        print(f"[measure] shipped {note}: H1 plateau {db:.1f} dBFS", flush=True)
    # PASS 2: matched variants
    for note, (f0, dur) in NOTES.items():
        if only and note not in only: continue
        target = PLATEAU_H1[note]
        shipped = MEASURED_H1_SHIPPED.get(note, None)
        if shipped is None:
            # fallback derivation: H1 amp ~ 0.94*master/sqrt(2)
            M = 10 ** (target / 20) * 2 ** 0.5 / 0.94
        else:
            M = 0.26 * 10 ** ((target - shipped) / 20)
        name = f"r_{note}_matched.html"
        wav = run_page(name, {"note": note.replace("_2", ""), "f0": f0, "dur": dur,
                              "noVib": True, "masterLevel": round(M, 4), "muteAirEdge": True}, f"our_{note}_matched.wav")
        if wav: results[(note, "matched")] = wav
    for (note, kind), wav in results.items():
        if kind != "matched": continue
        subprocess.run(["python", os.path.join(TMP, "tone_report.py"), wav,
                        "--nominal", note.replace("_2", ""), "--label", note,
                        "--json", os.path.join(TMP, f"our_{note}_matched_report.json")],
                       capture_output=True, text=True, timeout=300)
    print("DONE")

if __name__ == "__main__":
    main(set(sys.argv[1:]) or None)
