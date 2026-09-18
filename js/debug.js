// Dev audio-debug panel. Enable from the browser console with:
//   DEBUG=1        (DEBUG=0 hides it; `window.OCO_DEBUG.toggle()` also works)
// or by appending ?debug=1 to the page URL. Every slice of the voice — the
// base PeriodicWave harmonics, the tone lowpass, the high-note fade map and
// each layered partial — is exposed as a slider and applied to newly played
// notes. Tweaks persist in localStorage ("oco-debug-audio"); the panel
// restores itself on reload.
(function () {
  "use strict";
  var KEY = "oco-debug-audio";
  var OPEN_KEY = "oco-debug-open";
  var api = window.OCA_DEBUG;
  if (!api || !api.params) return; // audio.js missing or changed — bail quietly
  var P = api.params;
  var D = api.defaults;
  var on = false;
  var rows = [];      // { sync() } per slider row, for reset-all re-render
  var saveT = 0;
  var sweepT = 0;

  // ---- restore saved tweaks (only keys that still exist in the table) ----
  try {
    var saved = JSON.parse(localStorage.getItem(KEY) || "{}");
    Object.keys(saved).forEach(function (k) {
      if (k in D && typeof saved[k] === "number" && isFinite(saved[k])) P[k] = saved[k];
    });
  } catch (e) {}

  // ---- slider table: { t: group title, wave: rebuilds PeriodicWave, r: rows } ----
  // row = [param, label, min, max, step]
  var GROUPS = [
    { t: "Wave — pitch-keyed timbre", wave: 1, r: [
      // Global scales on the interpolated anchor curves (V_ANCHORS in
      // audio.js): every note rebuilds its wave from the pitch-keyed
      // profile, so these brighten/darken the whole range at once.
      ["h2Mul", "H2 scale (all notes)", 0, 3, 0.05],
      ["h3Mul", "H3 scale (all notes)", 0, 3, 0.05],
      ["h4Mul", "H4 scale (all notes)", 0, 3, 0.05],
      ["h5Mul", "H5 scale (all notes)", 0, 3, 0.05],
    ]},
    { t: "Measured-curve shape", r: [
      ["hardAmt", "Hard-blow drift", 0, 2, 0.05],
      ["levelCurveAmt", "Chamber level curve", 0, 2, 0.05],
      ["wanderAmt", "Slow pitch wander", 0, 2, 0.05],
      ["wobbleAmt", "Slow breath wobble", 0, 2, 0.05],
      ["windAmt", "Wind noise layer", 0, 2, 0.05],
    ]},
    { t: "Tone lowpass", r: [
      ["lpMult", "Cutoff \u00d7freq", 1, 20, 0.1],
      ["lpMax", "Cutoff cap Hz", 1000, 18000, 100],
      ["lpQ", "Q (resonance)", 0, 4, 0.05],
    ]},
    { t: "High-note fade map", r: [
      ["hiFrom", "Fade starts Hz", 200, 1600, 10],
      ["hiTo", "Fully faded Hz", 400, 2400, 10],
    ]},
    { t: "Air partial (detuned oct)", r: [
      ["airLevel", "Level", 0, 0.2, 0.002],
      ["airFade", "High-note fade", 0, 1, 0.05],
      ["airRatio", "Ratio \u00d7freq", 1.9, 3, 0.01],
    ]},
    { t: "Vibrato / tremolo (Zen only)", r: [
      ["vibRate", "Rate Hz", 1, 12, 0.1],
      ["vibDepth", "Pitch depth", 0, 0.02, 0.0005],
      ["vibHighFade", "Pitch high fade", 0, 1, 0.05],
      ["tremDepth", "Tremolo depth", 0, 0.3, 0.01],
      ["vibDelay", "Entry delay s", 0.05, 1, 0.05],
      ["zenPan", "Chorus spread L/R", 0, 1, 0.05],
    ]},
    { t: "Edge / windway whistle", r: [
      ["edgeBase", "Level base", 0, 0.2, 0.002],
      ["edgeReg", "Register boost", 0, 0.1, 0.002],
      ["edgeFade", "High-note fade", 0, 1, 0.05],
      ["edgeDet", "Detune", 0, 0.05, 0.001],
      ["edgeDetSpread", "Detune spread", 0, 0.03, 0.001],
      ["wanderDepth", "Pitch wander", 0, 0.03, 0.001],
      ["wanderFade", "Wander high fade", 0, 1, 0.05],
    ]},
    { t: "Onset — chiff & octave", r: [
      ["chiffScale", "Chiff level \u00d7", 0, 3, 0.05],
      ["chiffBase", "Chiff base s", 0.03, 0.2, 0.005],
      ["chiffSize", "Chiff chamber add s", 0, 0.2, 0.005],
      ["otBase", "Oct overtone level", 0, 0.5, 0.005],
      ["otEffort", "Overtone effort add", 0, 0.3, 0.005],
      ["otNoise", "Overtone noise mix", 0, 1, 0.05],
      ["otDurMax", "Oct decay max s", 0.04, 0.36, 0.005],
      ["otDurEffort", "Oct decay effort add s", 0, 0.2, 0.005],
    ]},
    { t: "Practice tuner (js/practice.js)", r: [
      ["tuneCents", "In-tune zone \u00A2", 0, 50, 1],
      ["transientCents", "Onset grace \u00A2", 0, 120, 5],
      ["transientMs", "Onset grace ms", 50, 400, 10],
      ["gapMs", "Attack gap ms", 50, 400, 10],
      ["rmsGate", "Mic silence gate", 0.002, 0.08, 0.002],
    ]},
    { t: "Output", r: [
      ["masterLevel", "Master level", 0.05, 1, 0.01],
      ["reverbWet", "Reverb wet", 0, 1, 0.01],
    ]},
  ];

  function dec(step) { return Math.max(0, (String(step).split(".")[1] || "").length); }
  function fmt(v, step) { return (+v).toFixed(dec(step)); }
  function clamp(v, lo, hi) { return Math.min(hi, Math.max(lo, v)); }

  function save() {
    clearTimeout(saveT);
    saveT = setTimeout(function () {
      try { localStorage.setItem(KEY, JSON.stringify(P)); } catch (e) {}
    }, 300);
  }

  // ---- panel skeleton ----
  var panel = document.createElement("div");
  panel.id = "dbgPanel";
  panel.innerHTML =
    '<div class="dbg-head">' +
      '<b>AUDIO DEBUG</b>' +
      '<span class="dbg-hint">console: DEBUG=1 / DEBUG=0</span>' +
      '<button class="dbg-x" type="button" title="Hide (or DEBUG=0)">\u2715</button>' +
    '</div>' +
    '<div class="dbg-tests">' +
      '<span class="dbg-testcap">Test:</span>' +
      '<span class="dbg-notes" id="dbgNotes"></span>' +
      '<button class="dbg-btn" type="button" id="dbgSweep">Sweep range</button>' +
      '<button class="dbg-btn" type="button" id="dbgStop">Stop</button>' +
      '<button class="dbg-btn" type="button" id="dbgWav" title="Capture what plays next for 3.5 s (single notes only; skips the output limiter) and download it as a WAV">\u2913 Export WAV</button>' +
      '<button class="dbg-btn" type="button" id="dbgLag" title="Fakes audio-clock starvation: triggers the perf fallback (red pulse + Lite proposal)">Induce lag</button>' +
    '</div>' +
    '<div id="dbgGroups"></div>' +
    '<div class="dbg-foot">' +
      '<button class="dbg-btn" type="button" id="dbgReset">Reset all</button>' +
      '<button class="dbg-btn" type="button" id="dbgCopy">Copy tweaks</button>' +
      '<span class="dbg-tip">applies to newly played notes \u00b7 auto-saved \u00b7 dbl-click a label to reset one value</span>' +
    '</div>';
  document.body.appendChild(panel);

  function playId(id, dur) {
    if (typeof playNote === "function") playNote(id, dur);
  }

  // ---- reference test notes: 5 evenly spaced across the instrument range ----
  // window.NOTES is installed asynchronously by app.js's boot(), so the
  // buttons are (re)built lazily: on open and whenever they're not ready.
  var notesHost = panel.querySelector("#dbgNotes");
  var builtFor = "";
  function ascNotes() {
    return (window.NOTES || []).slice().sort(function (a, b) { return freqOf(a) - freqOf(b); });
  }
  function buildNotes() {
    var list = ascNotes();
    var key = list.join(",");
    if (key === builtFor) return list;
    builtFor = key;
    notesHost.textContent = "";
    if (!list.length) {
      notesHost.textContent = "(no notes loaded)";
      return list;
    }
    [0, 0.25, 0.5, 0.75, 1].forEach(function (f) {
      var id = list[Math.round(f * (list.length - 1))];
      var b = document.createElement("button");
      b.className = "dbg-note";
      b.type = "button";
      b.textContent = id;
      b.title = freqOf(id).toFixed(1) + " Hz";
      b.addEventListener("click", function () { playId(id, 1.1); });
      notesHost.appendChild(b);
    });
    return list;
  }

  var sweepBtn = panel.querySelector("#dbgSweep");
  sweepBtn.addEventListener("click", function () {
    stopSweep();
    var list = buildNotes();
    if (!list.length) return;
    var i = 0;
    sweepT = setInterval(function () {
      if (i >= list.length) { stopSweep(); return; }
      playId(list[i++], 0.2);
    }, 240);
    sweepBtn.textContent = "\u2026 sweeping";
  });
  function stopSweep() {
    if (sweepT) { clearInterval(sweepT); sweepT = 0; }
    sweepBtn.textContent = "Sweep range";
  }

  panel.querySelector("#dbgStop").addEventListener("click", function () {
    stopSweep();
    if (typeof cutLive === "function") cutLive();
  });

  // ---- Induce lag: fakes audio-clock starvation so the perf fallback ----
  // (red-pulse button, Lite proposal toast, counters) can be exercised on
  // demand, without waiting for a real underrun.
  var lagBtn = panel.querySelector("#dbgLag");
  var lagT = 0;
  lagBtn.addEventListener("click", function () {
    if (!api || typeof api.simulateLag !== "function") return;
    api.simulateLag();
    var left = (typeof api.alertThrottleLeftMs === "function") ? api.alertThrottleLeftMs() : 0;
    if (left > 0) {
      // Raise still counts the glitch; only the toast/pulse is throttled.
      lagBtn.title = "Raise fires, toast throttled — retry in " + Math.ceil(left / 1000) + " s";
      clearTimeout(lagT);
      lagT = setTimeout(function () {
        lagBtn.title = "Fakes audio-clock starvation: triggers the perf fallback (red pulse + Lite proposal)";
      }, left + 500);
      return;
    }
    lagBtn.textContent = "\u2026 induced";
    setTimeout(function () { lagBtn.textContent = "Induce lag"; }, 1200);
  });

  // ---- WAV export: capture the next played note(s) for 3.5 s and download ----
  // Taps the reverb-bus input (dry source mix; the output limiter/headroom
  // stage is bypassed, so absolute levels read ~4.4 dB hotter than playback —
  // fine for spectral analysis, which is the point). Single notes only: a
  // loud chord can exceed ±1 and clamp in the 16-bit file.
  var wavBtn = panel.querySelector("#dbgWav");
  var wavTap = null, wavBlocks = null, wavN = 0, wavEl = null;
  function wavDone() {
    try { wavEl.removeEventListener("click", wavClick); } catch (e) {}
    if (wavEl) wavEl.textContent = "\u2913 Export WAV";
    wavEl = null;
  }
  function wavClick(ev) {
    ev.preventDefault();
    finishWav();
  }
  function finishWav() {
    if (!wavTap) { wavDone(); return; }
    try { wavTap.onaudioprocess = null; wavTap.disconnect(); } catch (e) {}
    // flush captured blocks into one buffer
    var flat = new Float32Array(wavN * 4096);
    for (var i = 0; i < wavN; i++) flat.set(wavBlocks[i], i * 4096);
    wavTap = null; wavBlocks = null; wavN = 0;
    // encode 16-bit mono WAV + download
    var n = flat.length;
    var buf = new ArrayBuffer(44 + n * 2), dv = new DataView(buf);
    var ws = function (off, str) { for (var i2 = 0; i2 < str.length; i2++) dv.setUint8(off + i2, str.charCodeAt(i2)); };
    ws(0, "RIFF"); dv.setUint32(4, 36 + n * 2, true); ws(8, "WAVE"); ws(12, "fmt ");
    dv.setUint32(16, 16, true); dv.setUint16(20, 1, true); dv.setUint16(22, 1, true);
    dv.setUint32(24, 44100, true); dv.setUint32(28, 88200, true); dv.setUint16(32, 2, true); dv.setUint16(34, 16, true);
    ws(36, "data"); dv.setUint32(40, n * 2, true);
    for (var j = 0; j < n; j++) {
      var v = Math.max(-1, Math.min(1, flat[j]));
      dv.setInt16(44 + j * 2, v < 0 ? v * 0x8000 : v * 0x7FFF, true);
    }
    var blob = new Blob([buf], { type: "audio/wav" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "ocarina_debug_export.wav";
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 5000);
    wavDone();
    console.log("[audio debug] WAV exported (" + (n / 44100).toFixed(2) + " s, 44.1 k mono 16-bit)");
  }
  wavBtn.addEventListener("click", function () {
    if (wavEl) { finishWav(); return; }  // second click truncates + saves
    try {
      audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      if (audioCtx.state === "suspended") audioCtx.resume();
      wavEl = wavBtn;
      wavBtn.textContent = "\u25cf recording next note\u2026";
      wavBlocks = [];
      wavN = 0;
      wavTap = audioCtx.createScriptProcessor(4096, 1, 1);
      wavTap.onaudioprocess = function (e) {
        if (wavBlocks) {
          wavBlocks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
          wavN++;
          if (wavN >= Math.ceil(3.5 * 44100 / 4096)) finishWav();
        }
      };
      (typeof getReverbBus === "function" ? getReverbBus(audioCtx) : audioCtx.destination).connect(wavTap);
      wavTap.connect(audioCtx.destination);
      // keep the capture armed even if the user plays within the panel
      wavEl.addEventListener("click", wavClick);
      console.log("[audio debug] capture armed \u2014 play a note now (single notes only)");
    } catch (e) {
      console.log("[audio debug] export failed: " + e);
      wavDone();
    }
  });

  // ---- slider rows ----
  function addRow(host, grp, row) {
    var k = row[0], label = row[1], min = row[2], max = row[3], step = row[4];
    var line = document.createElement("div");
    line.className = "dbg-row";
    var lab = document.createElement("span");
    lab.className = "dbg-lab";
    lab.textContent = label;
    lab.title = k + " \u00b7 dbl-click to reset";
    var rng = document.createElement("input");
    rng.type = "range"; rng.min = min; rng.max = max; rng.step = step; rng.value = P[k];
    var num = document.createElement("input");
    num.type = "number"; num.className = "dbg-num"; num.min = min; num.max = max; num.step = step;
    num.value = fmt(P[k], step);
    var rst = document.createElement("button");
    rst.className = "dbg-rst"; rst.type = "button"; rst.textContent = "\u21ba";
    rst.title = "Back to default (" + fmt(D[k], step) + ")";

    function sync() {
      var mod = Math.abs(P[k] - D[k]) > 1e-12;
      line.classList.toggle("mod", mod);
      rng.value = P[k];
      num.value = fmt(P[k], step);
    }

    function setVal(v) {
      var was = P[k];
      P[k] = clamp(+v || 0, min, max);
      sync();
      if (grp.wave) api.invalidateWave();
      if (k === "reverbWet") {
        // Re-ramp the live wet gain (setReverbEnabled re-reads the level).
        try { setReverbEnabled(reverbEnabled); } catch (e) {}
      }
      if (was !== P[k]) save();
    }

    rng.addEventListener("input", function () { setVal(rng.value); });
    num.addEventListener("change", function () { setVal(num.value); });
    rst.addEventListener("click", function () { setVal(D[k]); });
    lab.addEventListener("dblclick", function () { setVal(D[k]); });

    line.appendChild(lab);
    line.appendChild(rng);
    line.appendChild(num);
    line.appendChild(rst);
    host.appendChild(line);
    rows.push(sync);
  }

  var groupsHost = panel.querySelector("#dbgGroups");
  GROUPS.forEach(function (grp) {
    var det = document.createElement("details");
    det.className = "dbg-group";
    var sum = document.createElement("summary");
    sum.textContent = grp.t + (grp.wave ? " (rebuilds wave)" : "");
    det.appendChild(sum);
    var body = document.createElement("div");
    body.className = "dbg-rows";
    grp.r.forEach(function (row) { addRow(body, grp, row); });
    det.appendChild(body);
    groupsHost.appendChild(det);
  });

  // ---- footer buttons ----
  function resetAll() {
    Object.keys(D).forEach(function (k) { P[k] = D[k]; });
    api.invalidateWave();
    try { setReverbEnabled(reverbEnabled); } catch (e) {}
    rows.forEach(function (fn) { fn(); });
    save();
  }
  panel.querySelector("#dbgReset").addEventListener("click", resetAll);

  panel.querySelector("#dbgCopy").addEventListener("click", function () {
    var tweaked = {};
    Object.keys(D).forEach(function (k) {
      if (Math.abs(P[k] - D[k]) > 1e-12) tweaked[k] = P[k];
    });
    var keys = Object.keys(tweaked).sort();
    var s = "{\n" + keys.map(function (k) { return "  " + k + ": " + tweaked[k]; }).join(",\n") + "\n}";
    try { navigator.clipboard.writeText(JSON.stringify(tweaked)); } catch (e) {}
    console.log("[audio debug] off-default tweaks (raw JSON also on the clipboard):\n" + s);
  });

  // ---- show / hide ----
  function show(v) {
    on = !!v;
    panel.classList.toggle("open", on);
    if (on) {
      buildNotes();
      if (!(window.NOTES || []).length) pollNotes();
      else if (notePoll) { clearInterval(notePoll); notePoll = 0; }
    }
    rows.forEach(function (fn) { fn(); });
    try { localStorage.setItem(OPEN_KEY, on ? "1" : "0"); } catch (e) {}
  }

  // If the panel opens before app.js's boot() has installed the instrument,
  // poll briefly so the test-note buttons appear as soon as NOTES arrive.
  var notePoll = 0;
  function pollNotes() {
    if (notePoll) return;
    notePoll = setInterval(function () {
      if (buildNotes().length) { clearInterval(notePoll); notePoll = 0; }
    }, 400);
  }

  panel.querySelector(".dbg-x").addEventListener("click", function () { show(false); });

  // The console hook: `DEBUG=1` shows the panel, `DEBUG=0` hides it.
  try {
    Object.defineProperty(window, "DEBUG", {
      configurable: true,
      get() { return on ? 1 : 0; },
      set(v) { show(!(v == null || v === 0 || v === "0" || v === false)); },
    });
  } catch (e) {}

  // Initial state: URL flag, a DEBUG value set before load, or saved state.
  if (/[?&]debug=1\b/.test(location.search)) show(true);
  else if (window.DEBUG === 1 || window.DEBUG === "1") show(true);
  else {
    try { if (localStorage.getItem(OPEN_KEY) === "1") show(true); } catch (e) {}
  }

  // Public handle: window.OCO_DEBUG.{params, defaults, show, hide, toggle, resetAll, invalidateWave}
  api.show = function () { show(true); };
  api.hide = function () { show(false); };
  api.toggle = function () { show(!on); };
  api.resetAll = resetAll;
  window.OCO_DEBUG = api;

  // ---- Zen overlay: the panel is fixed on <body>, so real fullscreen ----
  // (Zen mode) paints the fullscreen element over it and the panel vanishes.
  // While anything is fullscreen we live INSIDE the fullscreen element
  // (always #tabPanel, the only fullscreen target in this app); on exit we
  // return to <body>. Relocation keeps all wiring (append, not recreate).
  var debugPanelBody = document.body;
  function zenRelocate() {
    if (!panel || !panel.parentElement) return;
    var fsEl = document.fullscreenElement || document.webkitFullscreenElement;
    if (fsEl && panel.parentElement !== fsEl) {
      debugPanelBody = panel.parentElement;
      fsEl.appendChild(panel);
    } else if (!fsEl && panel.parentElement !== debugPanelBody) {
      debugPanelBody.appendChild(panel);
    }
  }
  document.addEventListener("fullscreenchange", zenRelocate);
  document.addEventListener("webkitfullscreenchange", zenRelocate);
  if (document.fullscreenElement || document.webkitFullscreenElement) zenRelocate();
})();
