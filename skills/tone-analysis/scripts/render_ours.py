# render_ours.py — render the repo synth to WAV via headless-chrome
# OfflineAudioContext for the instrument-fit loop (the offline "testbench").
# audio.js is an ES module: the bench serves a PATCHED copy (imports re-pointed
# absolute, module-local freqOf override, dry render buses) and imports it as a
# real module — no classic-script shims.
#
# Render-path deviations from the shipped app (documented; they keep offline
# rendering from hanging and touch only inaudible-at-fit levels):
#   1. getReverbBus / getLiteBus bodies swapped for wire-through outGain(0.6)
#      (the always-connected 2.6 s convolver and the bus limiters hang or clip
#      offline; the app runs reverb OFF by default and the limiter rarely
#      engages, but drop it entirely so plateau comparisons stay linear).
#   2. air (osc #2), edge (#4), wander LFO (#5) are stubbed by muteAirEdge
#      (their combos hang offline; measurements below quantify their absence
#      against the recorded tone, the wind-noise layer still renders).
#   3. vibrato/tremolo can be disabled (--no-vib) for plateau takes.
#
# One page render per call, one fresh --user-data-dir per page, ~1.5 s gap.
#
# Usage:
#   python render_ours.py <note id> [:<dur>] [-o out.wav]
#        [--inst oot-alto-c-12] [--tone auto|none|<path>]
#        [--no-vib] [--no-wob] [--master-level 0.26] [--f0 HZ]
#   - note ids ride the instrument's fingerings.json; pitch is the chart's
#     ET frequency unless --f0 overrides (window.__F0 patched into the module).
import json, subprocess, os, re, sys, time, glob, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TMP = "/tmp/opencode" if os.path.isdir("/tmp/opencode") else os.path.join(REPO, "research", "analysis", "tmp")
JS = "http://127.0.0.1:8137/js"
PAGE = "http://127.0.0.1:8138"

def find_chrome():
    if os.environ.get("OCA_CHROME"): return os.environ["OCA_CHROME"]
    for cand in ["/usr/bin/google-chrome", "/usr/bin/chromium",
                 "/usr/bin/chromium-browser", shutil.which("chromium")]:
        if cand and os.path.exists(cand): return cand
    hits = sorted(glob.glob(os.path.expanduser(
        "~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome")))
    return hits[0] if hits else None

_fing_cache = {}

def fing_data(inst):
    if inst not in _fing_cache:
        _fing_cache[inst] = json.load(
            open(os.path.join(REPO, "instruments", inst, "fingerings.json"), encoding="utf-8"))
    return _fing_cache[inst]

def build_patched_module(inst, with_layers=False, wind=None, with_comp=False):
    # 1. all relative imports of the module graph resolve on the repo server
    #    (parse.js and friends keep re-importing each other relative to THEMSELVES);
    # 2. audio.js imports freqOf from music-math — the pitch override needs a
    #    module-local freqOf consulting window.__F0 first;
    # 3. the two bus builders swap for dry wire-through copies.
    src = open(os.path.join(REPO, "js", "audio.js"), encoding="utf-8-sig").read()
    src = src.replace('from "./', 'from "%s/' % JS)
    src = src.replace(
        'import { freqOf, quarterSecFor, tokenGridBeats } from',
        'import { freqOf as mathFreqOf, quarterSecFor, tokenGridBeats } from')
    src = src.replace(
        "import { isPracticeActive } from",
        "function freqOf(id) { if (typeof window !== \"undefined\" && window.__F0) return window.__F0; return mathFreqOf(id); }\n"
        "function STUB_OSC(ctx) { const sink = ctx.createGain(); return { type: \"sine\", frequency: sink.gain, detune: sink.gain, setPeriodicWave: function(){}, connect: function(){}, start: function(){}, stop: function(){} }; }\n"
        'import { isPracticeActive } from')
    # offline hang log: air, edge and its wander LFO must never create REAL
    # oscillators in an OfflineAudioContext. Stub them at their call sites so
    # the surrounding wiring stays intact (buffer layers keep rendering).
    # --with-comp: keep the app bus limiter in the rendered path (dry →
    # limiter(-6/6/12/0.006/0.2) → outGain 0.6 → destination, convolver still
    # out). The old offline hang was the compressor + tremolo passthrough
    # combo; the compressor alone renders here. Without this flag the bench
    # stays dry-wire (the historical comparison contract).
    # --with-layers skips the stubs for air/edge (the offline sensitivity
    # probes; wob LFOs stay real either way); expect possible hangs per the
    # bug log's combos rule.
    if not with_layers:
        src = src.replace("const air = ctx.createOscillator();",
                          "const air = STUB_OSC(ctx);")
    src = src.replace("const edge = ctx.createOscillator();",
                      "const edge = " + ("ctx.createOscillator()" if with_layers else "STUB_OSC(ctx)") + ";")
    src = src.replace("const wander = ctx.createOscillator();",
                      "const wander = " + ("ctx.createOscillator()" if with_layers else "STUB_OSC(ctx)") + ";")
    if with_comp:
        src = re.sub(r"function getReverbBus\(ctx\) \{.*?\n\}",
                     "function getReverbBus(ctx) {\n"
                     "  if (reverbBus && reverbBus.context === ctx) return reverbBus;\n"
                     "  const input = ctx.createGain();\n"
                     "  const dry = ctx.createGain();\n"
                     "  dry.gain.value = 1.0;\n"
                     "  const limiter = ctx.createDynamicsCompressor();\n"
                     "  limiter.threshold.value = -6;\n"
                     "  limiter.knee.value = 6;\n"
                     "  limiter.ratio.value = 12;\n"
                     "  limiter.attack.value = 0.006;\n"
                     "  limiter.release.value = 0.2;\n"
                     "  input.connect(dry); dry.connect(limiter);\n"
                     "  const outGain = ctx.createGain();\n"
                     "  outGain.gain.value = 0.6;\n"
                     "  limiter.connect(outGain); outGain.connect(ctx.destination);\n"
                     "  return reverbBus;\n"
                     "}", src, count=1)
    else:
        src = re.sub(r"function getReverbBus\(ctx\) \{.*?\n\}",
                 "function getReverbBus(ctx) {\n"
                 "  if (reverbBus && reverbBus.context === ctx) return reverbBus;\n"
                 "  const input = ctx.createGain();\n"
                 "  const outGain = ctx.createGain();\n"
                 "  outGain.gain.value = 0.6;\n"
                 "  input.connect(outGain); outGain.connect(ctx.destination);\n"
                 "  reverbBus = input;\n"
                 "  return reverbBus;\n"
                 "}", src, count=1)
    src = re.sub(r"function getLiteBus\(ctx\) \{.*?\n\}",
                 "function getLiteBus(ctx) {\n"
                 "  if (liteBus && liteBus.context === ctx) return liteBus;\n"
                 "  const input = ctx.createGain();\n"
                 "  const outGain = ctx.createGain();\n"
                 "  outGain.gain.value = 0.6;\n"
                 "  input.connect(outGain); outGain.connect(ctx.destination);\n"
                 "  liteBus = input;\n"
                 "  return liteBus;\n"
                 "}", src, count=1)
    # --wind bpQ,lpRatio,lpQ: re-target the WIND_SHAPE constants for shape
    # searches (the delivered chain differs from the analytic RBJ model, so
    # candidate constants must be verified through real renders).
    if wind and len(wind) == 3:
        rep = ("const WIND_SHAPE = { bumpRatio: 1.26, bumpQMax: %s, "
               "noiseLpRatio: %s, noiseLpQ: %s };" % tuple(wind))
        src = re.sub(r"const WIND_SHAPE = \{[^}]*\};", rep, src, count=1)
    out = os.path.join(TMP, "audio_patched.mjs")
    open(out, "w", encoding="utf-8").write(src)
    return out

TEMPLATE = r"""<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
<script type="importmap">
{ "imports": { "__JSURL__/audio.js": "__PAGE__/audio_patched.mjs" } }
</script>
<div id="OUT">PENDING</div><div id="ERR"></div>
<script>
const FING_DATA = __FING__;
const TONE_DATA = __TONE__;
const TWIN_DATA = __TWIN__;
const CFG = __CFG__;
</script>
<script type="module">
import { playNoteAt, installTwinModel } from "__PAGE__/audio_patched.mjs";
try {
window.FING = FING_DATA;
window.NOTES = FING_DATA.notes.map(function (n) { return n.id; });
window.DISPLAY = Object.fromEntries(FING_DATA.notes.map(function (n) { return [n.id, n.display]; }));
window.CHAMBER = Object.fromEntries(FING_DATA.notes.map(function (n) { return [n.id, n.chamber]; }));
window.COVER = Object.fromEntries(FING_DATA.notes.map(function (n) { return [n.id, n.covered]; }));
const OAC = window.OfflineAudioContext || window.webkitOfflineAudioContext;
const LEN = Math.ceil(44100 * (CFG.dur + 0.9));
window.AudioContext = function () {
  const o = new OAC(1, LEN, 44100);
  try { Object.defineProperty(o, "state", { get: function () { return "running"; }, configurable: true }); } catch (e) {}
  if (!o.resume) o.resume = function () { return Promise.resolve(); };
  window.__oac = o;
  return o;
};
if (TWIN_DATA && installTwinModel) installTwinModel(TWIN_DATA, CFG.instId);
if (window.OCA_DEBUG) {
  if (CFG.noVib) { OCA_DEBUG.params.vibDepth = 0; OCA_DEBUG.params.tremDepth = 0; }
  if (CFG.noWob) { OCA_DEBUG.params.wobbAmt = 0; OCA_DEBUG.params.wanderAmt = 0; }
  if (CFG.masterLevel !== undefined && CFG.masterLevel !== null) OCA_DEBUG.params.masterLevel = CFG.masterLevel;
  if (CFG.reverbWet !== undefined && CFG.reverbWet !== null) OCA_DEBUG.params.reverbWet = CFG.reverbWet;
  if (CFG.set) { for (const [k, v] of Object.entries(CFG.set)) OCA_DEBUG.params[k] = v; OCA_DEBUG.invalidateWave(); }
}
if (CFG.f0) window.__F0 = CFG.f0;
function encodeWav(f32, sr) {
  const n = f32.length;
  const buf = new ArrayBuffer(44 + n * 2), dv = new DataView(buf);
  const ws = function (o, str) { for (let i = 0; i < str.length; i++) dv.setUint8(o + i, str.charCodeAt(i)); };
  ws(0, "RIFF"); dv.setUint32(4, 36 + n * 2, true); ws(8, "WAVE"); ws(12, "fmt ");
  dv.setUint32(16, 16, true); dv.setUint16(20, 1, true); dv.setUint16(22, 1, true);
  dv.setUint32(24, sr, true); dv.setUint16(28, sr * 2, true); dv.setUint16(32, 2, true); dv.setUint16(34, 16, true);
  ws(36, "data"); dv.setUint32(40, n * 2, true);
  for (let i = 0; i < n; i++) {
    const v = Math.max(-1, Math.min(1, f32[i]));
    dv.setInt16(44 + i * 2, v < 0 ? v * 0x8000 : v * 0x7FFF, true);
  }
  return new Uint8Array(buf);
}
function b64(buf8) {
  let s = ""; const CH = 0x8000;
  for (let i = 0; i < buf8.length; i += CH) s += String.fromCharCode.apply(null, buf8.subarray(i, i + CH));
  return btoa(s);
}
if (CFG.note) playNoteAt(CFG.note, CFG.when == null ? null : CFG.when, CFG.dur, __BAG__);
if (CFG.seq && CFG.seq.length) {
  // melody-sequence audit: absolute offline-clock starts, notes touch
  // each other (no gap) so the transition behavior is what gets measured.
  let t0 = CFG.seqStart;
  for (const s of CFG.seq) {
    playNoteAt(s.note, t0, s.dur, []);
    t0 += s.dur;
  }
}
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

_httpds = []

def ensure_servers():
    import http.server, threading, socketserver, functools
    if _httpds: return
    class Quiet(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        protocol_version = "HTTP/1.0"
        def end_headers(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            super().end_headers()
    for port, root in ((8137, REPO), (8138, TMP)):
        class H(Quiet, http.server.SimpleHTTPRequestHandler):
            pass
        socketserver.ThreadingTCPServer.allow_reuse_address = True
        try:
            httpd = socketserver.ThreadingTCPServer(
                ("127.0.0.1", port), functools.partial(H, directory=root))
        except OSError:
            continue  # something already serves this port (a manual server)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        _httpds.append(httpd)

CHROME = None

def run_page(name, cfg, out_wav, wind=None, with_comp=False):
    ensure_servers()
    build_patched_module(cfg.get("instId", "oot-alto-c-12"), wind=wind,
                         with_comp=with_comp)
    page = TEMPLATE.replace("__FING__", json.dumps(cfg.get("_fing"))).replace(
        "__TONE__", json.dumps(cfg.get("_tone"))).replace(
        "__TWIN__", json.dumps(cfg.get("_twin"))).replace(
        "__BAG__", json.dumps(cfg.get("_bag") or [])).replace(
        "__CFG__", json.dumps({k: v for k, v in cfg.items() if not k.startswith("_")})).replace(
        "__PAGE__", PAGE).replace("__JSURL__", JS)
    html = os.path.join(TMP, name)
    open(html, "w", encoding="utf-8").write(page)
    # Playwright drives the page in real time (OfflineAudioContext + virtual
    # time budget never resolves startRendering on this chrome; the old
    # dump-dom pipeline predates the module-era audio.js).
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        page = browser.new_page()
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)[:200]))
        page.goto(f"{PAGE}/{name}")
        try:
            page.wait_for_function(
                "document.getElementById('OUT').textContent !== 'PENDING'",
                timeout=max(20000, int(cfg["dur"] * 1000) + 35000))
        except Exception:
            pass
        out = page.evaluate("document.getElementById('OUT').textContent")
        browser.close()
    m = re.match(r"B64:", out)
    if errs and not m:
        print(f"[{name}] PAGEERROR: {errs[:2]}", flush=True)
    if not m:
        print(f"[{name}] FAILED: {out[:200]}", flush=True)
        return None
    os.makedirs(os.path.dirname(out_wav), exist_ok=True)
    open(out_wav, "wb").write(base64.b64decode(out[4:]))
    print(f"[{name}] -> {out_wav}", flush=True)
    time.sleep(1.5)
    return out_wav

def main():
    argv = sys.argv[1:]
    def opt(flag, default=None):
        return argv[argv.index(flag) + 1] if flag in argv else default
    spec = next((a for a in argv if not a.startswith("-") and a), "")
    note_id, _, dur_s = spec.partition(":")
    dur = float(dur_s) if dur_s else 2.0
    out = opt("-o")
    inst = opt("--inst", "oot-alto-c-12")
    tone = opt("--tone", "auto")
    seq_spec = opt("--seq")
    if not out:
        base = os.path.join(REPO, "research", "analysis", "12hole", "renders")
        out = os.path.join(base, f"{inst}_{note_id}.wav")
    build_patched_module(inst)
    if seq_spec:
        seq = []
        total = 0.0
        for part in seq_spec.split(","):
            n, _, d = part.partition(":")
            d = float(d) if d else 0.35
            seq.append({"note": n, "dur": d})
            total += d
        lead = float(opt("--lead", "0.05"))
        cfg = {"seq": seq, "seqStart": lead, "instId": inst,
               "dur": round(lead + total + 1.2, 3),
               "_fing": fing_data(inst)}
    else:
        cfg = {"note": note_id, "instId": inst, "dur": dur,
               "_fing": fing_data(inst)}
    if tone == "auto":
        path = os.path.join(REPO, "instruments", inst, "tone.json")
        cfg["_tone"] = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None
    elif tone == "none":
        cfg["_tone"] = None
    else:
        cfg["_tone"] = json.load(open(tone, encoding="utf-8"))
    # Candidate magnitudes for the absolute noise-body layer: injected into
    # the tone's global gate (park/warm/rough db), so matrix rounds render
    # candidates without rewriting tone.json. Requires a loaded tone model.
    gk = {}
    for flag, key, seed in (("--parkDb", "windPark", {"f": 273, "Q": 2.2}),
                            ("--warmDb", "windWarm", {"f": 470, "Q": 0.8}),
                            ("--roughDb", "windRough", {})):
        v = opt(flag)
        if v is not None and cfg.get("_tone"):
            seed["db"] = float(v)
            gk[key] = seed
    if gk:
        cfg["_tone"].setdefault("global", {}).update(gk)
    if "--no-vib" in argv: cfg["noVib"] = True
    if "--no-wob" in argv: cfg["noWob"] = True
    ml = opt("--master-level")
    if ml is not None: cfg["masterLevel"] = float(ml)
    wind = opt("--wind")
    build_patched_module(inst, wind=wind.split(",") if wind else None)
    sets = []
    for a in argv:
        if a.startswith("--set:") and "=" in a:
            k, v = a[6:].partition("=")[0], float(a[6:].partition("=")[2])
            sets.append([k, v])
    if sets:
        cfg["set"] = dict((k, v) for k, v in sets)
    f0 = opt("--f0")
    if f0 is not None: cfg["f0"] = float(f0)
    run_page(f"r12_{note_id or 'seq'}_{int(dur*1000)}.html", cfg, out,
             wind=[s.strip() for s in wind.split(",")] if wind else None,
             with_comp="--with-comp" in argv)

import base64

if __name__ == "__main__":
    main()
