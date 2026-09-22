let APP_CSS = "";
let lastTokens = [];
let liveIdx = -1;
let displayMode = "grid"; // "grid" | "scroll" | "single"
let zenPrevMode = null;

function fitInput() {
  const ta = document.getElementById("src");
  if (!ta) return;
  ta.style.height = "auto";
  ta.style.height = Math.max(74, ta.scrollHeight) + "px";
}

function isLiveTab() {
  return displayMode === "single";
}

function isScrollMode() {
  return displayMode === "scroll";
}

function updateModeButtons() {
  document.querySelectorAll("#modeSeg .seg-btn").forEach(b => {
    const on = b.dataset.mode === displayMode;
    b.classList.toggle("on", on);
    b.setAttribute("aria-checked", on ? "true" : "false");
    // Radiogroup roving tabindex: only the checked mode is a tab stop;
    // arrows carry the rest (see the keydown wiring on the segment below).
    b.setAttribute("tabindex", on ? "0" : "-1");
  });
}

function setDisplayMode(m) {
  if (m !== "grid" && m !== "scroll" && m !== "single") return;
  if (displayMode === m) return;
  displayMode = m;
  if (m !== "single") resetLiveTab();
  updateModeButtons();
  render();
  syncFocusMode();
}

function resetLiveTab() {
  liveIdx = -1;
}

function cueFirstNote() {
  const toks = lastTokens.length ? lastTokens : parse(document.getElementById("src").value);
  if (!toks.length) return;
  const i = firstSoundIdx(toks);
  const t = toks[i];
  highlightToken(i, t && t.id);
  scrollFocusStripTo(i);
}

function firstSoundIdx(tokens) {
  const i = tokens.findIndex(t => t.type === "note" || t.type === "rest" || t.type === "tie");
  return i < 0 ? 0 : i;
}

function isPitched(t) {
  return t && (t.type === "note" || t.type === "tie") && NOTES.includes(t.id);
}

function loopOn() {
  const el = document.getElementById("loopMel");
  return !!(el && el.checked);
}

function nextPitchToken(tokens, idx) {
  for (let i = idx + 1; i < tokens.length; i++) {
    if (isPitched(tokens[i])) return tokens[i];
  }
  if (loopOn()) {
    for (let i = 0; i < idx; i++) {
      if (isPitched(tokens[i])) return tokens[i];
    }
  }
  return null;
}

function beatsToDurLabel(beats) {
  const map = [
    [4, 1, false], [3, 2, true], [2, 2, false], [1.5, 4, true],
    [1, 4, false], [0.75, 8, true], [0.5, 8, false], [0.375, 16, true], [0.25, 16, false]
  ];
  for (const [b, d, dot] of map) {
    if (Math.abs(beats - b) < 1e-6) return durLabel(d, dot);
  }
  return null;
}

function combinedDurLabel(tokens, idx) {
  const total = soundingGridBeats(tokens, idx);
  const single = beatsToDurLabel(total);
  if (single) return single;
  const parts = [durLabel(tokens[idx].dur, tokens[idx].dotted, tokens[idx].triplet)];
  for (let i = idx + 1; i < tokens.length; i++) {
    if (tokens[i].type === "bar" || tokens[i].type === "bass") continue;
    if (tokens[i].type === "tie") parts.push(durLabel(tokens[i].dur, tokens[i].dotted, tokens[i].triplet));
    else break;
  }
  return parts.join("+");
}

function rangeLabel() {
  const r = (typeof FING !== "undefined" && FING) ? FING.range : null;
  if (!r) return "";
  const lo = (window.DISPLAY && DISPLAY[r.low]) || pretty(r.low);
  const hi = (window.DISPLAY && DISPLAY[r.high]) || pretty(r.high);
  return lo + "–" + hi;
}

function tallyTokens(tokens) {
  const problems = [];
  let notes = 0, outOf = 0, switches = 0, prevCh = null;
  tokens.forEach(t => {
    if (t.type === "bar" || t.type === "rest" || t.type === "tempo" || t.type === "bass") return;
    if (t.type === "tie") {
      // A tie after an out-of-range pitch is ITSELF out of range (that's how
      // "A6/2 -/4" reads on an alto C): the sheet draws it as a marked oor tie
      // card, so count it in the same bucket instead of shouting "(nothing to
      // continue)" — the tie did have something to continue; it just can't
      // sound. The !t.id arm stays as unreachable-by-parser safety net.
      if (t.id && !NOTES.includes(t.id) && isOutOfRange(t.id)) { outOf++; return; }
      if (!t.id || !NOTES.includes(t.id)) problems.push((t.raw || "-") + " (nothing to continue)");
      return;
    }
    if (!NOTES.includes(t.id)) {
      // Out-of-range notes are NOT listed here: the tablature section already
      // surfaces them loudly (range-warn banner + the marked cards), so
      // echoing every one into the input panel's error line just stacks
      // redundant text. #err stays for genuine input problems only.
      outOf++;
      return;
    }
    notes++;
    const ch = CHAMBER[t.id];
    if (prevCh && ch !== prevCh) switches++;
    prevCh = ch;
  });
  return { notes, outOf, switches, problems };
}

function appendNoteCard(sheet, t, i) {
  const id = t.id;
  if (!NOTES.includes(id)) {
    const rc = rangeCheck(id);
    const r = document.createElement("div");
    r.dataset.i = String(i);
    if (rc === "below" || rc === "above") {
      const arrow = rc === "below" ? "\u2193" : "\u2191";
      const dir = rc === "below" ? "below" : "above";
      r.className = "card oor " + (rc === "below" ? "oor-low" : "oor-high");
      r.title = pretty(id) + " is " + dir + " this ocarina's range (" + rangeLabel() + ")";
      r.innerHTML = `<div class="compact oor-mark">${arrow}</div>
        <div class="meta"><span class="nm">${pretty(id)}</span>
        <span class="badge oor-badge">${dir} range</span>
        <span class="dur">${durLabel(t.dur, t.dotted, t.triplet)}</span></div>`;
    } else {
      r.className = "rest";
      r.style.borderColor = "var(--accent)"; r.style.color = "var(--accent)";
      r.textContent = (t.raw || id) + " ✕";
    }
    sheet.appendChild(r);
    return;
  }
  const ch = CHAMBER[id];
  const card = document.createElement("div");
  card.className = "card" + (ch ? " ch" + ch : "");
  card.dataset.i = String(i);
  card.innerHTML = `<div class="compact">${ocarinaSVG(COVER[id] || [], ch)}</div>
    <div class="meta"><span class="nm">${spelledLabel(t)}${t.staccato ? '<span class="stac-mark" title="staccato (short, with a pause)">\u2022</span>' : ''}</span>
     <span class="dur">${durLabel(t.dur, t.dotted, t.triplet)}</span></div>`;
  sheet.appendChild(card);
}

function fillFullSheet(sheet, tokens, sectioned = true) {
  sheet.classList.remove("live");
  tokens.forEach((t, i) => {
    if (t.type === "bass") return; // hidden support marker
    // Junk chips belong to the token strip and the reading strip only: a
    // chart card would sit between fingering cards and wreck the grid's
    // rhythm (the card path highlights tolerate a missing data-i anyway).
    if (t.type === "bad") return;
    if (t.type === "bar") {
      // A named bar OPENS a section: in row layouts (grid + print) its name
      // gets a full-width .sec-head row and the measure line is dropped — the
      // section header replaces it (a row-leading zero-width line would
      // otherwise dangle outside the sheet's left edge, it has nothing to its
      // left to sit between). The scroll band has no header row, so its
      // tagged line stays there.
      if (sectioned && t.desc) {
        const h = document.createElement("div");
        h.className = "sec-head";
        h.textContent = t.desc;
        sheet.appendChild(h);
        return;
      }
      const b = document.createElement("div"); b.className = "tab-bar";
      if (t.desc) { b.classList.add("has-note"); b.title = t.desc; }
      sheet.appendChild(b); return;
    }
    if (t.type === "tempo") {
      const tp = document.createElement("div"); tp.className = "tab-tempo";
      tp.dataset.i = String(i);
      tp.textContent = "♩=" + t.bpm;
      sheet.appendChild(tp); return;
    }
    if (t.type === "rest") {
      const r = document.createElement("div"); r.className = "card rest";
      r.dataset.i = String(i);
      r.innerHTML = `<div class="compact">rest</div>
        <div class="meta"><span></span>
        <span class="dur">${durLabel(t.dur, t.dotted, t.triplet)}</span></div>`;
      sheet.appendChild(r); return;
    }
    if (t.type === "tie") {
      if (!t.id || !NOTES.includes(t.id)) {
        if (isOutOfRange(t.id)) {
          const rc = rangeCheck(t.id);
          const dir = rc === "below" ? "below" : "above";
          const r = document.createElement("div");
          r.className = "card rest tie oor " + (rc === "below" ? "oor-low" : "oor-high");
          r.dataset.i = String(i);
          r.title = "continues " + pretty(t.id) + " (" + dir + " this ocarina's range)";
          r.innerHTML = `<div class="compact">–</div>
            <div class="meta"><span class="nm">–</span>
            <span class="dur">${durLabel(t.dur, t.dotted, t.triplet)}</span></div>`;
          sheet.appendChild(r); return;
        }
        const r = document.createElement("div"); r.className = "rest";
        r.style.borderColor = "var(--accent)"; r.style.color = "var(--accent)";
        r.dataset.i = String(i);
        r.textContent = (t.raw || "-") + " ✕"; sheet.appendChild(r); return;
      }
      const r = document.createElement("div"); r.className = "card rest tie";
      const tieCh = t.id && CHAMBER[t.id];
      if (tieCh) r.classList.add("ch" + tieCh);
      r.dataset.i = String(i);
      r.innerHTML = `<div class="compact">–</div>
        <div class="meta"><span class="nm">–</span>
        <span class="dur">${durLabel(t.dur, t.dotted, t.triplet)}</span></div>`;
      sheet.appendChild(r); return;
    }
    appendNoteCard(sheet, t, i);
  });
}

function liveCardHtml(t, tokens, i) {
  if (t.type === "rest") {
    const nxt = nextPitchToken(tokens, i);
    const id = nxt ? nxt.id : null;
    const ch = id ? CHAMBER[id] : 1;
    const svg = ocarinaSVG(id ? (COVER[id] || []) : [], ch);
    return `<div class="compact">
        <div class="live-oca">${svg}</div>
        <div class="rest-over">rest</div>
      </div>
      <div class="meta"><span class="nm">rest</span>
        <span class="dur">${durLabel(t.dur, t.dotted, t.triplet)}</span></div>`;
  }
  const id = t.id;
  if ((t.type === "note" || t.type === "tie") && NOTES.includes(id)) {
    const ch = CHAMBER[id];
    return `<div class="compact">${ocarinaSVG(COVER[id] || [], ch)}</div>
      <div class="meta"><span class="nm">${spelledLabel(t)}${t.staccato ? '<span class="stac-mark" title="staccato (short, with a pause)">\u2022</span>' : ''}</span>
        <span class="dur">${combinedDurLabel(tokens, i)}</span></div>`;
  }
  if ((t.type === "note" || t.type === "tie") && isOutOfRange(id)) {
    return liveOorHtml(t);
  }
  return `<div class="compact"></div><div class="meta"><span class="nm">${t.raw || ""} ✕</span></div>`;
}

function liveOorHtml(t) {
  const rc = rangeCheck(t.id);
  const arrow = rc === "below" ? "\u2193" : "\u2191";
  const dir = rc === "below" ? "below" : "above";
  return `<div class="compact oor-mark">${arrow}</div>
    <div class="meta"><span class="nm">${pretty(t.id)}</span>
      <span class="badge oor-badge">${dir} range</span>
      <span class="dur">${durLabel(t.dur, t.dotted, t.triplet)}</span></div>`;
}

function fillLiveSheet(sheet, tokens, idx) {
  sheet.classList.remove("scroll");
  sheet.classList.add("live");
  let i = idx;
  if (i == null || i < 0 || !tokens[i] || tokens[i].type === "bar" || tokens[i].type === "bass") i = firstSoundIdx(tokens);
  if (!tokens.length || i < 0 || !tokens[i] || tokens[i].type === "bar" || tokens[i].type === "bass") return;
  const card = document.createElement("div");
  const t = tokens[i];
  const liveCh = t.id && NOTES.includes(t.id) && CHAMBER[t.id];
  card.className = "card live" + (t.type === "rest" ? " is-rest" : "") +
    (isOutOfRange(t.id) ? " oor" : "") +
    (liveCh ? " ch" + liveCh : "");
  card.dataset.i = String(i);
  if (t.id) card.dataset.pitch = t.id;
  card.innerHTML = liveCardHtml(t, tokens, i);
  sheet.appendChild(card);
}

function updateLiveTab(tokens, idx) {
  const sheet = document.getElementById("sheet");
  if (!sheet || !isLiveTab()) return;
  let i = idx;
  if (i == null || i < 0 || !tokens[i] || tokens[i].type === "bar") i = firstSoundIdx(tokens);
  const t = tokens[i];
  if (!t) return;
  const card = sheet.querySelector(".card.live");
  const holdSame = card && !card.classList.contains("is-rest") &&
    (t.type === "note" || t.type === "tie") && t.id && card.dataset.pitch === t.id;
  if (holdSame) {
    card.dataset.i = String(i);
    card.classList.add("now");
    if (t.type === "note") {
      const dur = card.querySelector(".dur");
      if (dur) dur.textContent = combinedDurLabel(tokens, i);
    }
    return;
  }
  sheet.innerHTML = "";
  fillLiveSheet(sheet, tokens, i);
  const next = sheet.querySelector(".card.live");
  if (next) next.classList.add("now");
  // The card just rebuilt — an integrated practice tuner must move into it
  // immediately (renderPanel's safety net would otherwise be a tick late).
  if (typeof practiceRelocatePanel === "function") practiceRelocatePanel();
}

function updateRangeWarning(outOf) {
  let bar = document.getElementById("rangeWarn");
  const panel = document.getElementById("tabPanel");
  if (!outOf) {
    if (bar) bar.hidden = true;
    return;
  }
  if (!bar && panel) {
    bar = document.createElement("div");
    bar.id = "rangeWarn";
    bar.className = "range-warn";
    bar.setAttribute("role", "alert");
    panel.insertBefore(bar, panel.firstChild);
  }
  if (!bar) return;
  const inst = window.CURRENT_INSTRUMENT;
  const name = inst ? [inst.type, inst.version].filter(Boolean).join(" · ") : "this ocarina";
  const n = outOf === 1 ? "1 note is" : outOf + " notes are";
  bar.innerHTML = `<span class="rw-icon" aria-hidden="true">\u26A0</span>` +
    `<span>${n} outside ${name} (range ${rangeLabel()}). ` +
    `Out-of-range notes are marked below and can't be played.</span>`;
  bar.hidden = false;
}

function render() {
  try {
    if (typeof currentTemplatePath === "function" && typeof ensureOcarinaTemplate === "function") {
      const path = currentTemplatePath();
      if (path && path !== installedTplPath) {
        ensureOcarinaTemplate().then(changed => { if (changed) render(); });
        return;
      }
    }
    const src = document.getElementById("src").value;
    fitInput();
    document.getElementById("title").textContent = titleFromText(src);
    const typedSwing = swingFromText(src);
    applySwing(typedSwing != null ? typedSwing : 0);
    const tokens = parse(src);
    lastTokens = tokens;
    drawTokens(tokens);
    const sheet = document.getElementById("sheet");
    const err = document.getElementById("err");
    sheet.innerHTML = "";
    const { notes, outOf, switches, problems } = tallyTokens(tokens);
    if (isLiveTab()) {
      sheet.classList.remove("scroll");
      fillLiveSheet(sheet, tokens, liveIdx);
    } else {
      sheet.classList.toggle("scroll", isScrollMode());
      // Section headers belong to row/grid layouts: the scroll band is a
      // nowrap strip where a full-width header row cannot fit.
      fillFullSheet(sheet, tokens, !isScrollMode());
    }
    updateRangeWarning(outOf);
    // Out-of-range info lives in the tablature section (banner + marked
    // cards) — #err carries only genuine input problems, so no has-oor magic.
    err.textContent = problems.join(" · ");
    document.getElementById("stats").textContent =
      notes ? `${notes} notes · ${switches} chamber switch${switches===1?"":"es"}` : "Type or click a melody.";
    if (typeof syncFocusMode === "function") syncFocusMode();
  } catch (e) {
    const err = document.getElementById("err");
    if (err) err.textContent = "Render error: " + e;
    console.error(e);
  }
}

function quarterSec() {
  // Base tempo of the CURRENT SONG: its own leading "# tempo" header (the
  // same the inline "# tempo" tokens start from), else 100. The tempo slider
  // is a RELATIVE playback speed (10–100%) applied at scheduling time in
  // audio.js (tempoPct), not an absolute BPM — moving it mid-song only
  // affects notes scheduled after the move.
  const ta = document.getElementById("src");
  const t = (ta && tempoFromText(ta.value)) || 100;
  return 60 / Math.max(10, Math.min(400, t || 100));
}

function tokenSeconds(tokOrDur, dotted) {
  const beats = (tokOrDur && typeof tokOrDur === "object")
    ? (tokOrDur.beats || 1)
    : (4 / (tokOrDur || 4)) * (dotted ? 1.5 : 1);
  return Math.max(0.12, beats * quarterSec());
}

function highlightToken(i, noteId, durSec, sounding) {
  liveIdx = i;
  const lite = typeof liteMode === "function" && liteMode();
  document.querySelectorAll(".tok.now, .card.now, .rest.now, .key.now").forEach(el => el.classList.remove("now"));
  document.querySelectorAll('.tok[data-i="' + i + '"]').forEach(el => el.classList.add("now"));
  // The focus strip is the reading line in Zen — keep it moving even in Lite
  // (smooth scrolling is browser-native and cheap; Lite still skips the
  // sheet auto-scroll and the glow below). Practice mode follows it too: the
  // reading line should track the note the player is about to hit.
  if (isMelodyPlaying() ||
      (typeof isPracticeActive === "function" && isPracticeActive())) {
    scrollFocusStripTo(i);
  }
  if (isLiveTab()) {
    updateLiveTab(lastTokens.length ? lastTokens : parse(document.getElementById("src").value), i);
  } else {
      const card = document.querySelector('.card[data-i="' + i + '"], .rest[data-i="' + i + '"]');
      if (card) {
        card.classList.add("now");
        const sheet = document.getElementById("sheet");
        if (sheet && sheet.classList.contains("scroll") && !lite) {
          const wrap = sheet.parentElement;
          if (wrap) {
            const inset = 16;
            const toks = lastTokens.length ? lastTokens : parse(document.getElementById("src").value);
            // Default cadence: at every bar, re-anchor the playing card to the
            // left inset. Mid-bar, catch up early — as soon as the NEXT card
            // pokes past the inset, align the playing card to the left so the
            // upcoming card is revealed without waiting for it to overlap.
            const barStart = atBarStart(toks, i);
            let move = barStart;
            if (!barStart) {
              const nk = nextCardIdx(toks, i);
              const next = nk >= 0 ? document.querySelector('.card[data-i="' + nk + '"], .rest[data-i="' + nk + '"]') : null;
              if (next) {
                const nc = next.getBoundingClientRect();
                const nw = wrap.getBoundingClientRect();
                move = nc.right > nw.right - inset || nc.left < nw.left + inset;
              }
            }
            if (move) {
              const w = wrap.getBoundingClientRect();
              const delta = card.getBoundingClientRect().left - (w.left + inset);
              animatedScrollTo(wrap, Math.max(0, wrap.scrollLeft + delta));
            }
          }
        }
      }
  }
  if (noteId) {
    document.querySelectorAll('.key[data-note="' + noteId + '"]').forEach(el => el.classList.add("now"));
    if (sounding && !lite) pulseZenGlow(noteId, durSec);
  }
}

// Mellow ambient glow in Zen/focus mode: map the note's pitch to a hue
// (low = warm amber, high = cool teal/violet), swell the glow up, HOLD it for
// the body of the note, then fade out to the note's end so sustained notes
// keep their light and short notes pulse briefly.
function noteMidi(id) {
  const m = String(id).match(/^([A-G]s?)(\d)$/);
  if (!m) return 69;
  const semi = {C:0,Cs:1,D:2,Ds:3,E:4,F:5,Fs:6,G:7,Gs:8,A:9,As:10,B:11};
  return semi[m[1]] + (+m[2] + 1) * 12;
}
let zenGlowFadeTimer = 0;
function pulseZenGlow(noteId, durSec) {
  const panel = document.getElementById("tabPanel");
  if (!panel || !panel.classList.contains("focus")) return;
  const lo = 57, hi = 91; // A3 .. G6
  const t = Math.max(0, Math.min(1, (noteMidi(noteId) - lo) / (hi - lo)));
  // Low = warm amber, mid = teal; high notes desaturate and brighten toward
  // white so they stand out against the dark warm background (purple did not).
  const hue = Math.round(30 + t * 160);        // 30° amber → 190° teal (no purple)
  const sat = Math.round(72 - t * t * 72);     // high notes fully desaturate → white
  const light = Math.round(50 + t * t * 48);   // high notes brighten to ~98% → white
  const dur = (durSec && durSec > 0 ? durSec : 0.4) * 1000; // ms
  // The glow swells across almost the whole note, peaking near the end, then a
  // short fade. Short notes still rise quickly enough to register.
  const fade = Math.min(500, Math.max(220, dur * 0.25)); // short tail
  const rise = Math.max(160, dur - fade);                // build over the note body
  // Glow reach: short notes keep the halo tight around the card, long notes
  // swell it out into the screen margins.
  const startScale = 0.7;
  const fullScale = Math.min(1.25, startScale + dur / 3000); // grows with duration

  clearTimeout(zenGlowFadeTimer);
  panel.style.setProperty("--glow-hue", hue);
  panel.style.setProperty("--glow-sat", sat + "%");
  panel.style.setProperty("--glow-light", light + "%");
  // Center the halo on the fingering card (its center may sit below the panel
  // center due to the title/transport). Measured relative to the panel.
  const card = panel.querySelector(".card.live") ||
               panel.querySelector(".sheet.live .card") ||
               panel.querySelector("svg.ocarina");
  if (card) {
    const p = panel.getBoundingClientRect();
    const c = card.getBoundingClientRect();
    if (p.width && p.height) {
      panel.style.setProperty("--glow-x", ((c.left + c.width / 2 - p.left) / p.width * 100) + "%");
      panel.style.setProperty("--glow-y", ((c.top + c.height / 2 - p.top) / p.height * 100) + "%");
    }
  }
  // Commit the small/dim START state instantly (no transition), then flip to
  // the END state so opacity+scale interpolate over `rise` and the peak lands
  // near the note's end.
  panel.style.setProperty("--glow-fade", "0ms");
  panel.style.setProperty("--glow-alpha", "0");
  panel.style.setProperty("--glow-scale", startScale);
  void panel.offsetWidth; // force reflow so the start state is committed
  panel.style.setProperty("--glow-fade", rise + "ms");
  // Peak intensity scales with pitch (high = white/bright) AND note length:
  // short notes stay dim, long sustained notes build to the full bright glow.
  const durF = Math.min(1, dur / 1200); // ramps in over ~1.2s of sustain
  const peak = (0.28 + t * t * 0.4) * (0.45 + 0.55 * durF);
  panel.style.setProperty("--glow-alpha", peak.toFixed(3));
  panel.style.setProperty("--glow-scale", fullScale);
  // Fade out over the final short tail.
  zenGlowFadeTimer = setTimeout(() => {
    panel.style.setProperty("--glow-fade", fade + "ms");
    panel.style.setProperty("--glow-alpha", "0");
  }, rise);
}

// Immediately dim the zen glow and cancel any pending swell/fade — used when
// playback pauses/stops mid-note so the light doesn't keep animating on its own.
function freezeZenGlow() {
  const panel = document.getElementById("tabPanel");
  clearTimeout(zenGlowFadeTimer);
  if (!panel) return;
  panel.style.setProperty("--glow-fade", "260ms");
  panel.style.setProperty("--glow-alpha", "0");
}

// True when token i is the first sounding card of its bar (bars and inline
// tempo markers are zero-time boundaries).
function atBarStart(toks, i) {
  let k = i - 1, sawBreak = false;
  while (k >= 0) {
    const t = toks[k];
    if (t.type === "bar" || t.type === "tempo") { sawBreak = true; k--; }
    else if (t.type === "bass") k--; // hidden marker: transparent, no break
    else break;
  }
  return sawBreak || i === 0;
}

// Index of the next sounding card (note/tie/rest) after token i, skipping
// zero-time bar/tempo tokens; -1 when none remains.
function nextCardIdx(toks, i) {
  for (let k = i + 1; k < toks.length; k++) {
    const t = toks[k];
    if (t.type === "note" || t.type === "tie" || t.type === "rest") return k;
    if (t.type !== "bar" && t.type !== "tempo" && t.type !== "bass") break;
  }
  return -1;
}

let sheetScrollRaf = 0;
// The sheet scroll should stay readable but quick: a short ease-out glide of
// ~2px/ms (60–160ms), so bar jumps are perceived as motion, not teleports —
// and never lag behind the playing notes.
function animatedScrollTo(wrap, target) {
  if (sheetScrollRaf) cancelAnimationFrame(sheetScrollRaf);
  const from = wrap.scrollLeft, dist = target - from;
  if (Math.abs(dist) < 1) { wrap.scrollLeft = target; sheetScrollRaf = 0; return; }
  const dur = Math.max(60, Math.min(160, Math.abs(dist) / 2));
  const t0 = performance.now();
  const ease = x => 1 - Math.pow(1 - x, 3);
  const step = now => {
    const p = Math.min(1, (now - t0) / dur);
    wrap.scrollLeft = from + dist * ease(p);
    sheetScrollRaf = p < 1 ? requestAnimationFrame(step) : 0;
  };
  sheetScrollRaf = requestAnimationFrame(step);
}

function scrollFocusStripTo(i) {
  const strip = document.getElementById("focusTokens");
  if (!strip || !strip.offsetParent) return;
  const el = strip.querySelector('.tok[data-i="' + i + '"]');
  if (!el) return;
  const s = strip.getBoundingClientRect();
  const c = el.getBoundingClientRect();
  const delta = (c.left + c.width / 2) - (s.left + s.width / 2);
  // Big jumps (e.g. loop wrap back to the start) snap instantly; small steps glide.
  const behavior = Math.abs(delta) > s.width ? "auto" : "smooth";
  strip.scrollTo({ left: Math.max(0, strip.scrollLeft + delta), behavior });
}

function clearHighlight() {
  document.querySelectorAll(".tok.now, .card.now, .rest.now, .key.now").forEach(el => el.classList.remove("now"));
}

// Hover/arrow preview: the HIGHLIGHT is immediate; the note is deliberately
// DELAYED — it only sounds after pointer/arrow settles on the token for
// HOVER_HEAR_MS. Grazing the strip while moving across the screen (or
// sweeping arrow keys through the melody) must not machine-gun notes;
// resting on one is the deliberate "listen" (matching hover/arrow equally).
// Both inputs go through this one scheduler: a newer preview cancels the
// pending one, so only the token you settle on is heard.
const HOVER_HEAR_MS = 260;
let hoverVoiceTimer = 0, hoverVoiceToken = null;

function hushTokenHover() {
  if (hoverVoiceTimer) { clearTimeout(hoverVoiceTimer); hoverVoiceTimer = 0; }
  hoverVoiceToken = null;
}

function hoverPreview(i, t) {
  if (isMelodyPlaying() || hoverQuietUntil > Date.now()) return;
  // Practicing owns the glow and the sounds: token hovers would inject
  // playback-mode pulses over the fill-driven halo.
  if (typeof isPracticeActive === "function" && isPracticeActive()) return;
  highlightToken(i, t.id);
  // Same token already dwelling — don't re-arm, that would defeat the delay.
  if (hoverVoiceTimer && hoverVoiceToken === t) return;
  hushTokenHover();
  hoverVoiceToken = t;
  hoverVoiceTimer = setTimeout(() => {
    hoverVoiceTimer = 0;
    // Re-check at fire time: the melody may have started, or a redraw
    // began a new quiet window while the pointer rested here.
    if (isMelodyPlaying() || hoverQuietUntil > Date.now()) { hushTokenHover(); return; }
    if (typeof isPracticeActive === "function" && isPracticeActive()) return;
    unlockAudio();
    if (!audioCtx || audioCtx.state !== "running") return;
    playNote(t.id, Math.min(tokenSeconds(t), 0.5));
  }, HOVER_HEAR_MS);
}

// Similarly to hover — silent: keyboard focus must not make noise; Enter on
// the token is the deliberate "make noise" path.
function tokenFocusPreview(i, t) {
  if (isMelodyPlaying()) return;
  if (typeof isPracticeActive === "function" && isPracticeActive()) return;
  highlightToken(i, t.id);
}

// Touch has no hover: HOLD-to-hear rides the same dwell as the mouse/arrow
// path (hoverPreview's HOVER_HEAR_MS). A quick tap keeps the native click's
// meaning (play from here); the click is swallowed only after a COMPLETED
// hold, so the listen it already produced must not also start the transport.
// Drift (finger sliding = scroll intent) cancels like a mouseleave.
let touchHoldHeard = false;
function wireTokenTouch(el, i, t) {
  let origin = null;
  const calm = () => {
    hushTokenHover();
    if (!isMelodyPlaying()) clearHighlight();
  };
  el.addEventListener("touchstart", (e) => {
    if (e.touches.length !== 1) return; // pinch = zoom, not a dwell
    origin = null;
    hoverPreview(i, t);
    // The dwell must actually have armed (quiet windows / running melody /
    // practice mode make the preview a no-op — then we own no gesture).
    if (hoverVoiceToken === t && hoverVoiceTimer) {
      origin = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    }
  });
  el.addEventListener("touchmove", (e) => {
    if (!origin) return;
    const p = e.touches[0];
    if (Math.hypot(p.clientX - origin.x, p.clientY - origin.y) > 12) {
      origin = null;
      calm(); // drift = scroll intent
    }
  });
  const lift = () => {
    if (!origin) return;
    origin = null;
    if (hoverVoiceTimer) calm(); // released before the dwell: silent cancel
    else touchHoldHeard = true;  // the preview already spoke; swallow the tap
  };
  el.addEventListener("touchend", lift);
  el.addEventListener("touchcancel", () => { origin = null; calm(); });
}

// Roving tab stop for a token strip: one tab stop per strip (a song strip can
// hold hundreds of tokens — tabbing through all of them is unusable).
let tokAnchor = {};
function tokAnchorSet(box, i) {
  tokAnchor[box.id] = i;
  [...box.querySelectorAll('.tok[role="button"]')].forEach(el =>
    el.tabIndex = +el.dataset.i === i ? 0 : -1);
}

function wireTokenKeydown(el, box) {
  el.addEventListener("keydown", e => {
    // Enter only: Space belongs to the global play/pause shortcut
    // (wireSpacebar) — locally intercepting both made Space produce a
    // click-pause mash: a short faint note.
    if (e.key === "Enter") {
      e.preventDefault();
      hushTokenHover();       // committing to playback: no pending preview
      el.click();             // "play from here" (or practice re-anchor)
      return;
    }
    const toks = [...box.querySelectorAll('.tok[role="button"]')];
    const i = toks.indexOf(el);
    if (i < 0) return;
    let n = null;
    if (e.key === "ArrowRight") n = (i + 1) % toks.length;
    else if (e.key === "ArrowLeft") n = (i - 1 + toks.length) % toks.length;
    else if (e.key === "Home") n = 0;
    else if (e.key === "End") n = toks.length - 1;
    if (n == null || !toks[n]) return;
    e.preventDefault();
    tokAnchorSet(box, +toks[n].dataset.i);
    toks[n].focus();
    // Arrow-walk mirrors hovering: passing over the melody hears it only
    // when you settle. The dwell scheduler inside hoverPreview cancels the
    // previous token's pending note, so sweeping arrows stays silent.
    const t = lastTokens && lastTokens[+toks[n].dataset.i];
    if (t && (t.type === "note" || t.type === "tie") && t.id && NOTES.includes(t.id))
      hoverPreview(+toks[n].dataset.i, t);
  });
}

function buildTokenEl(t, i) {
  if (t.type === "bass") return null; // hidden support marker
  const el = document.createElement("span");
  el.dataset.i = String(i);
  el.style.cursor = "pointer";
  el.title = "click or Enter = play from here";
  if (t.type === "bar") {
    el.className = "tok bar";
    el.textContent = "|";
    if (t.desc) {
      el.classList.add("has-note");
      el.title = t.desc;
    }
  } else if (t.type === "tempo") {
    el.className = "tok tempo";
    el.textContent = "♩=" + t.bpm;
    el.title = "tempo changes to " + t.bpm + " BPM from here";
  } else if (t.type === "rest") {
    el.className = "tok pause";
    el.innerHTML = `r <span class="td">${durLabel(t.dur, t.dotted, t.triplet)}</span>`;
  } else if (t.type === "tie") {
    if (t.id && NOTES.includes(t.id)) {
      el.className = "tok tie ch" + CHAMBER[t.id];
      el.innerHTML = `– <span class="td">${durLabel(t.dur, t.dotted, t.triplet)}</span>`;
      el.addEventListener("mouseenter", () => hoverPreview(i, t));
      el.addEventListener("mouseleave", () => {
        hushTokenHover();
        if (!isMelodyPlaying()) clearHighlight();
      });
      wireTokenTouch(el, i, t);
      el.addEventListener("focus", () => tokenFocusPreview(i, t));
      el.addEventListener("blur", () => {
        hushTokenHover();
        if (!isMelodyPlaying()) clearHighlight();
      });
    } else if (isOutOfRange(t.id)) {
      const rc = rangeCheck(t.id);
      const dir = rc === "below" ? "below" : "above";
      el.className = "tok tie oor " + (rc === "below" ? "oor-low" : "oor-high");
      el.title = "continues " + pretty(t.id) + " (" + dir + " this ocarina's range)";
      el.innerHTML = `– <span class="td">${durLabel(t.dur, t.dotted, t.triplet)}</span>`;
    } else {
      el.className = "tok bad";
      el.textContent = t.raw || "-";
    }
  } else if (t.type === "bad") {
    // Junk the grammar surfaced: show raw text + what to do about it.
    el.className = "tok bad";
    el.textContent = t.raw || "?";
    el.title = "not part of the melody notation — fix or remove it";
  } else if (!NOTES.includes(t.id)) {
    const rc = rangeCheck(t.id);
    if (rc === "below" || rc === "above") {
      el.className = "tok oor " + (rc === "below" ? "oor-low" : "oor-high");
      const arrow = rc === "below" ? "\u2193" : "\u2191";
      el.title = pretty(t.id) + " is " + (rc === "below" ? "below" : "above") + " this ocarina's range (" + rangeLabel() + ")";
      el.innerHTML = `${arrow} ${pretty(t.id)}`;
    } else {
      el.className = "tok bad";
      el.textContent = t.raw || t.id;
      el.title = "not a playable note";
    }
  } else {
    el.className = "tok ch" + CHAMBER[t.id];
    const slide = t.slide ? `<span class="slide-mark" title="slide from ${pretty(t.slideFrom)}">\u21DD</span>` : "";
    const stac = t.staccato ? `<span class="stac-mark" title="staccato (short, with a pause)">\u2022</span>` : "";
    el.innerHTML = `${slide}${spelledLabel(t)}${stac} <span class="td">${durLabel(t.dur, t.dotted, t.triplet)}</span>`;
    if (t.slide) el.classList.add("slide");
    if (t.staccato) el.classList.add("staccato");
    el.addEventListener("mouseenter", () => hoverPreview(i, t));
    el.addEventListener("mouseleave", () => {
      hushTokenHover();
      if (!isMelodyPlaying()) clearHighlight();
    });
    wireTokenTouch(el, i, t);
    el.addEventListener("focus", () => tokenFocusPreview(i, t));
    el.addEventListener("blur", () => {
      hushTokenHover();
      if (!isMelodyPlaying()) clearHighlight();
    });
  }
  // While practicing, the same click re-anchors the practice from this token
  // instead of starting normal playback.
  el.addEventListener("click", e => {
    if (touchHoldHeard) { touchHoldHeard = false; return; }
    e.preventDefault(); unlockAudio();
    if (typeof isPracticeActive === "function" && isPracticeActive()) {
      if (window.OCA_PRACTICE) OCA_PRACTICE.from(i);
    } else playMelody(i);
  });
  // Keyboard operability: every activatable token is role=button. Unparseable
  // ("bad") tokens carry no action, so they stay plain text for AT too.
  if (!el.classList.contains("bad")) {
    el.tabIndex = -1;                        // roving anchor assigned in drawTokenStrip
    el.setAttribute("role", "button");
    const nm = t.id && NOTES.includes(t.id) ? pretty(t.id) : "";
    el.setAttribute("aria-label", nm ? "Play from " + nm : "Play from here");
  }
  return el;
}

function drawTokenStrip(box, tokens, sectioned) {
  if (!box) return;
  // Was a token in this strip focused before the rebuild? Editing usually
  // rebuilds while the textarea holds focus, but keyboard navigation can
  // leave focus here when a redraw arrives (e.g. instrument swap).
  const prevFocusI = box.contains(document.activeElement) && document.activeElement.dataset
    ? document.activeElement.dataset.i : null;
  box.innerHTML = "";
  tokens.forEach((t, i) => {
    // Playback strip (sectioned): a named bar starts a new section — put its
    // name on its own header row before the tokens resume. The Zen reading
    // strip stays a flat line of tokens.
    if (sectioned && t.type === "bar" && t.desc) {
      const h = document.createElement("div");
      h.className = "sec-head";
      h.textContent = t.desc;
      box.appendChild(h);
    }
    const el = buildTokenEl(t, i);
    if (el) {
      box.appendChild(el);
      if (el.hasAttribute("role")) wireTokenKeydown(el, box);
    }
  });
  // Roving anchor: restore the previous anchor index when sane, else the
  // first activatable token; return focus to the token that had it.
  let anchor = tokAnchor[box.id];
  const roles = [...box.querySelectorAll('.tok[role="button"]')];
  let anchorEl = anchor != null
    ? roles.find(el => +el.dataset.i === anchor)
    : null;
  if (!anchorEl) anchorEl = roles[0] || null;
  if (anchorEl) {
    anchor = +anchorEl.dataset.i;
    tokAnchorSet(box, anchor);
  }
  let refocus = null;
  if (prevFocusI != null) {
    const again = [...box.querySelectorAll('.tok')].find(el => el.dataset.i === prevFocusI);
    if (again && again.hasAttribute("role")) refocus = again;
  }
  if (refocus) refocus.focus();
}

function drawTokens(tokens) {
  hoverQuietUntil = Date.now() + 400;
  drawTokenStrip(document.getElementById("tokens"), tokens, true);
  drawTokenStrip(document.getElementById("focusTokens"), tokens);
}

function addNote(id) {
  const ta = document.getElementById("src");
  const needsSpace = ta.value.length && !/\s$/.test(ta.value);
  ta.value += (needsSpace ? " " : "") + pretty(id);
  clearLibrarySelection();
  render();
}

// Piano press in single mode: show the note's fingering in the live card,
// exactly like hovering that note's token does. The card is built from a
// synthesized token (no score position) so it doesn't touch liveIdx and the
// next real highlight replaces it naturally. Skipped while a melody plays:
// there the live card belongs to the playback highlight.
function pianoPreviewToken(id) {
  const m = /^(.)(s?)(\d+)$/.exec(String(id));
  return {
    type: "note", id,
    dur: 4, dotted: false, triplet: false, beats: 1,
    spellLetter: m ? m[1] : id[0],
    spellAcc: m && m[2] === "s" ? "#" : "",
    spellOct: m ? m[3] : "",
  };
}

function pianoNotePreview(id) {
  if (!isLiveTab() || !NOTES.includes(id) || isMelodyPlaying()) return;
  const sheet = document.getElementById("sheet");
  if (!sheet) return;
  sheet.innerHTML = "";
  sheet.classList.remove("scroll");
  sheet.classList.add("live");
  const card = document.createElement("div");
  const previewCh = CHAMBER[id];
  card.className = "card live now" + (previewCh ? " ch" + previewCh : "");
  card.dataset.pitch = id; // no dataset.i: not a score position
  // One-token array (i=0) so combinedDurLabel stays well-defined — the card
  // then shows the ordinary quarter-label slot, no tie chain.
  card.innerHTML = liveCardHtml(pianoPreviewToken(id), [pianoPreviewToken(id)], 0);
  sheet.appendChild(card);
}

// Piano keyboard: keyboard-operable like the rest of the UI. Keys are
// role=button with a roving tabindex (one tab stop for the whole keyboard).
// Left/Right step chromatically, Up/Down move an octave, Home/End jump to the
// ends; Enter auditions the focused key and Space stays the global
// pause/continue shortcut. Clicking keeps the roving anchor on the pressed
// key, so arrows continue from where the mouse left off.
function kbRoving(kb, active) {
  [...kb.querySelectorAll(".key[data-note]")].forEach(k =>
    k.tabIndex = k === active ? 0 : -1);
}

function kbWire(kb) {
  if (!kb.dataset.kbWired) {
    kb.dataset.kbWired = "1";
    kb.addEventListener("keydown", e => {
      const el = e.target;
      if (!el.classList || !el.classList.contains("key") || !el.dataset.note) return;
      if (e.key === "Enter") {
        e.preventDefault();
        el.click();           // reuses the mouse handler (audition + preview)
        return;
      }
      const keys = [...kb.querySelectorAll(".key[data-note]")];
      const i = keys.indexOf(el);
      if (i < 0) return;
      let n = null;
      if (e.key === "ArrowRight") n = (i + 1) % keys.length;
      else if (e.key === "ArrowLeft") n = (i - 1 + keys.length) % keys.length;
      else if (e.key === "ArrowUp") n = (i + 12) % keys.length;
      else if (e.key === "ArrowDown") n = (i - 12 + keys.length) % keys.length;
      else if (e.key === "Home") n = 0;
      else if (e.key === "End") n = keys.length - 1;
      if (n == null || !keys[n]) return;
      e.preventDefault();     // navigation must not scroll the page
      kbRoving(kb, keys[n]);
      keys[n].focus();
      // No audition on mere navigation — Enter is the loud path. Space falls
      // through to the global pause/continue shortcut on purpose.
    });
  }
  kb.setAttribute("role", "group");
  kb.setAttribute("aria-label", "Piano keyboard");
}

function buildKB() {
  const kb = document.getElementById("kb");
  kb.innerHTML = "";
  kbWire(kb);
  const whites = ["C","D","E","F","G","A","B"];
  const blackAfter = {C:"Cs", D:"Ds", F:"Fs", G:"Gs", A:"As"};
  // Octaves 2-7: the contrabass range (B2-F4) through the bass (A3-G6) and
  // alto top (C7 lives in octave 7); keys outside an instrument's range
  // render dimmed, so the extra bottom octave costs nothing unless it's used.
  for (const oct of [2, 3, 4, 5, 6, 7]) {
    const col = document.createElement("div"); col.className = "oct";
    for (const w of whites) {
      const cell = document.createElement("div"); cell.className = "pkey";
      const id = w + oct;
      const k = document.createElement("div"); k.className = "key";
      if (NOTES.includes(id)) {
        k.dataset.note = id;
        k.tabIndex = -1;                       // roving anchor picked after build
        k.setAttribute("role", "button");
        k.setAttribute("aria-label", "Hear " + pretty(id));
        k.title = id + " — click hear, right-click add";
        k.innerHTML = `<span class="n">${w}${oct===4?"":oct}</span>`;
        k.onclick = () => { kbRoving(kb, k); playNote(id); pianoNotePreview(id); };
        k.oncontextmenu = e => { e.preventDefault(); kbRoving(kb, k); playNote(id); addNote(id); pianoNotePreview(id); };
      } else {
        k.style.opacity = .25;
      }
      cell.appendChild(k);
      const line = document.createElement("div");
      line.className = "ch-line";
      if (NOTES.includes(id)) line.classList.add("c" + CHAMBER[id]);
      cell.appendChild(line);
      const sh = blackAfter[w];
      if (sh) {
        const sid = sh + oct;
        const b = document.createElement("div"); b.className = "key black";
        if (NOTES.includes(sid)) {
          b.dataset.note = sid;
          b.tabIndex = -1;
          b.setAttribute("role", "button");
          b.setAttribute("aria-label", "Hear " + pretty(sid));
          b.title = sid + " — click hear, right-click add";
          b.onclick = () => { kbRoving(kb, b); playNote(sid); pianoNotePreview(sid); };
          b.oncontextmenu = e => { e.preventDefault(); kbRoving(kb, b); playNote(sid); addNote(sid); pianoNotePreview(sid); };
        } else {
          b.style.opacity = .2;
        }
        cell.appendChild(b);
      }
      col.appendChild(cell);
    }
    kb.appendChild(col);
  }
  const first = kb.querySelector(".key[data-note]");
  if (first) first.tabIndex = 0;
}

function pageCss() {
  if (APP_CSS) return APP_CSS;
  try {
    return [...document.styleSheets].map(ss =>
      [...ss.cssRules].map(r => r.cssText).join("\n")
    ).join("\n");
  } catch (e) {
    return "";
  }
}

function tabsFileStem() {
  const song = (document.getElementById("title").textContent || "").trim();
  const inst = window.CURRENT_INSTRUMENT;
  const instBit = inst && inst.type ? inst.type : "";
  const raw = [song || "ocarina-tabs", instBit].filter(Boolean).join(" - ");
  return raw.replace(/[^\w\- ]+/g, "").replace(/\s+/g, " ").trim() || "ocarina-tabs";
}

function printableHtml() {
  const title = document.getElementById("title").textContent || "Ocarina Practice";
  const css = pageCss();
  const tmp = document.createElement("div");
  tmp.className = "sheet";
  fillFullSheet(tmp, lastTokens.length ? lastTokens : parse(document.getElementById("src").value));
  const sheet = tmp.innerHTML;
  const heading = title.replace(/[<>&]/g, c => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" }[c]));
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${heading}</title>
<style>${css}
body{background:#fff}
header.app,.panel:first-of-type{display:none}
.wrap{max-width:none;padding:12px}
@media print { @page { margin: 10mm; } }
</style></head>
<body>
<h1 style="font:650 18px/1.3 system-ui;margin:0 0 12px">${heading}</h1>
<div id="sheet" class="sheet">${sheet}</div>
</body></html>`;
}

function persistPlayHeaders() {
  const ta = document.getElementById("src");
  if (!ta) return;
  // The tempo header is the SONG's own — never the relative playback dial.
  ta.value = withPlayHeaders(ta.value, null, songTempo(), currentSwing());
  fitInput();
}

function wireUi() {
  document.getElementById("playMel").onclick = transportEngagePlay;
  const pracBtn = document.getElementById("practiceBtn");
  if (pracBtn) pracBtn.onclick = transportEngagePractice;
  const pracFocusBtn = document.getElementById("practiceFocusBtn");
  if (pracFocusBtn) pracFocusBtn.onclick = transportEngagePractice;
  const liteCb = document.getElementById("liteMel");
  if (liteCb) {
    try { if (localStorage.getItem("oco-lite") === "1") liteCb.checked = true; } catch (e) {}
    liteCb.addEventListener("change", () => {
      try { localStorage.setItem("oco-lite", liteCb.checked ? "1" : "0"); } catch (e) {}
    });
  }
  const tempoEl = document.getElementById("tempo");
  if (tempoEl) {
    tempoEl.addEventListener("input", () => {
      applyTempoPct(+tempoEl.value);
      persistPlayHeaders();
    });
  }
  const focusTempoEl = document.getElementById("focusTempo");
  if (focusTempoEl) {
    focusTempoEl.addEventListener("input", () => {
      applyTempoPct(+focusTempoEl.value);
      persistPlayHeaders();
    });
  }
  const swingEl = document.getElementById("swing");
  const swingVal = document.getElementById("swingVal");
  if (swingEl && swingVal) {
    swingEl.addEventListener("input", () => {
      swingVal.textContent = swingEl.value;
      persistPlayHeaders();
    });
  }
  document.getElementById("print").onclick = () => {
    const html = printableHtml();
    const w = window.open("", "_blank");
    if (w) {
      w.document.write(html);
      w.document.close();
      w.focus();
      setTimeout(() => { try { w.print(); } catch (e) {} }, 250);
    } else {
      safeAlert("Popup blocked — use Download tabs instead.");
    }
  };
  document.getElementById("download").onclick = () => {
    const blob = new Blob([printableHtml()], {type: "text/html"});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = tabsFileStem() + ".html";
    a.click();
    // Same-tick revoke can abort downloads in some engines; drain later.
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  };
  document.getElementById("clear").onclick = () => {
    document.getElementById("src").value = "";
    clearLibrarySelection();
    resetLiveTab();
    if (typeof practiceInvalidate === "function") try { practiceInvalidate(); } catch (e) {}
    render();
  };
  document.getElementById("src").addEventListener("input", () => {
    // Typed edits replace the melody the session was built from — end it so
    // the next Practice press starts fresh on the edited song.
    if (typeof practiceInvalidate === "function") try { practiceInvalidate(); } catch (e) {}
    render();
  });
  const big = document.getElementById("bigSmall");
  if (big) big.onclick = () => {
    const on = big.getAttribute("aria-pressed") !== "true";
    big.setAttribute("aria-pressed", on ? "true" : "false");
    big.classList.toggle("on", on);
    render();
  };
  document.querySelectorAll("#modeSeg .seg-btn").forEach(b => {
    b.onclick = () => setDisplayMode(b.dataset.mode);
  });
  {
    // Radiogroup arrow behaviour: arrows move focus AND selection, wrapping
    // at the ends; Enter/Space stay native-button (Space is the global
    // pause/continue shortcut and must not re-select here).
    const segBtns = [...document.querySelectorAll("#modeSeg .seg-btn")];
    const segMove = (from, dir) => {
      const to = (from + dir + segBtns.length) % segBtns.length;
      setDisplayMode(segBtns[to].dataset.mode);
      segBtns[to].focus();
    };
    segBtns.forEach((b, i) => {
      b.addEventListener("keydown", (e) => {
        if (e.key === "ArrowRight" || e.key === "ArrowDown") { e.preventDefault(); segMove(i, +1); }
        else if (e.key === "ArrowLeft" || e.key === "ArrowUp") { e.preventDefault(); segMove(i, -1); }
        else if (e.key === "Home") { e.preventDefault(); segMove(i, -i); }
        else if (e.key === "End") { e.preventDefault(); segMove(i, segBtns.length - 1 - i); }
      });
    });
  }
  updateModeButtons();
  const fsBtn = document.getElementById("fullscreen");
  if (fsBtn) fsBtn.onclick = () => {
    // Full screen keeps whatever display is active (grid/scroll/single all
    // fullscreen fine); only Zen forces the single-ocarina view. Without the
    // Fullscreen API (e.g. iPhone Safari / ?nofs=1) the button still gets a
    // chrome-less view via the CSS fallback — without the zen behaviour.
    if (document.body.classList.contains("zen-fallback")) { exitFullscreenFallback(); return; }
    const panel = document.getElementById("tabPanel");
    if (canFullscreen(panel)) toggleFullscreen(panel); else enterFullscreenFallback();
  };
  document.addEventListener("mousemove", revealZenUi);
  const shareBtn = document.getElementById("shareZen");
  if (shareBtn) shareBtn.onclick = copyShareZenLink;
  wireZen();
  perfRelocate();
  wirePerfAlerts();
  window.addEventListener("resize", () => { if (perfOpen) clampPerfPop(); });
  wireCollapsers();
  wireFocusControls();
  wireSpacebar();
  updateTransportUI();
}

let zenUiTimer = 0;
function revealZenUi() {
  const p = document.getElementById("tabPanel");
  if (!p || !p.classList.contains("focus")) return;
  p.classList.add("ui-visible");
  if (zenUiTimer) clearTimeout(zenUiTimer);
  zenUiTimer = setTimeout(() => p.classList.remove("ui-visible"), 2500);
}

function wireFocusControls() {
  const pp = document.getElementById("focusPlay");
  const st = document.getElementById("focusStop");
  const lp = document.getElementById("focusLoop");
  const ex = document.getElementById("focusExit");
  if (pp) pp.onclick = () => { unlockAudio(); transportEngagePlay(); };
  if (st) st.onclick = () => {
    // Full reset of whichever mode owns the transport.
    if (typeof isPracticeActive === "function" && isPracticeActive() && window.OCA_PRACTICE) {
      OCA_PRACTICE.stop();
      return;
    }
    stopMelody();
  };
  if (lp) lp.onclick = () => {
    const cb = document.getElementById("loopMel");
    if (cb) cb.checked = !cb.checked;
    syncLoopUI();
  };
  const loopCb = document.getElementById("loopMel");
  if (loopCb) loopCb.addEventListener("change", syncLoopUI);
  if (ex) ex.onclick = () => toggleZen();
  const strip = document.getElementById("focusTokens");
  if (strip) {
    strip.addEventListener("wheel", e => {
      const d = Math.abs(e.deltaY) > Math.abs(e.deltaX) ? e.deltaY : e.deltaX;
      if (!d) return;
      e.preventDefault();
      strip.scrollLeft += d;
    }, { passive: false });
  }
  syncLoopUI();
}

function syncLoopUI() {
  const cb = document.getElementById("loopMel");
  const lp = document.getElementById("focusLoop");
  if (!lp) return;
  const on = !!(cb && cb.checked);
  lp.classList.toggle("on", on);
  lp.setAttribute("aria-pressed", on ? "true" : "false");
}

function isFocusMode() {
  const p = document.getElementById("tabPanel");
  return !!(p && p.classList.contains("focus"));
}

function syncFocusMode() {
  const panel = document.getElementById("tabPanel");
  if (!panel) return;
  const on = isFullscreen() && isLiveTab();
  panel.classList.toggle("focus", on);
    if (on) {
      applyTempoPct(tempoPct());
      syncLoopUI();
      revealZenUi();
      const toks = lastTokens.length ? lastTokens : parse(document.getElementById("src").value);
      scrollFocusStripTo(liveIdx >= 0 ? liveIdx : firstSoundIdx(toks));
    }
    if (typeof perfRelocate === "function") perfRelocate();
    // Re-seat the practice tuner for the new layout (body ↔ #tabPanel) and
    // re-clamp its dragged position into the viewport.
    if (typeof practiceRelocatePanel === "function") practiceRelocatePanel();
}

function updateTransportUI() {
  // Three symmetric states: play running, practice running, neither (paused).
  // Both buttons stay ENABLED at all times — that is what makes the swap
  // seamless (the other button switches modes from the current position, the
  // active one disengages). Active = colored, paused = neutral.
  const pracRuns = (typeof isPracticeActive === "function" && isPracticeActive()) &&
    !(typeof isPracticePaused === "function" && isPracticePaused());
  const playing = (typeof isMelodyPlaying === "function" && isMelodyPlaying());
  // The playback-only dials shape playback only — practice ignores them, so
  // they DIM while practice is engaged. Opacity only (never hidden): the zen
  // bar keeps its geometry (no jump) and restore is automatic.
  const tempoOff = (typeof isPracticeActive === "function" && isPracticeActive());
  const tg = document.getElementById("tempoGrp");
  if (tg) tg.classList.toggle("dial-off", tempoOff);
  const ft = document.getElementById("focusTempoLab");
  if (ft) ft.classList.toggle("dial-off", tempoOff);
  const main = document.getElementById("playMel");
  if (main) {
    // The button PAUSES (resume on the next click) — say so; a real stop is
    // the transport's ⏹ (zen) or a song/library change. "Stop" read like
    // losing the position, which it never did.
    main.textContent = playing ? "Pause" : "Play";
    // Neutral (idle/paused) is outline — never the black filled look.
    main.classList.toggle("on", playing);
  }
  ["practiceBtn", "practiceFocusBtn"].forEach(id => {
    const b = document.getElementById(id);
    if (!b) return;
    b.classList.toggle("on", pracRuns);
    b.setAttribute("aria-pressed", pracRuns ? "true" : "false");
  });
  const fp = document.getElementById("focusPlay");
  if (fp) {
    // The transport glyphs are inline SVG (index.html): the class flip alone
    // switches play ↔ pause. Never write textContent here — it would wipe
    // the svg children.
    fp.classList.toggle("is-playing", playing);
  }
}

// The two transports engage / swap / disengage symmetrically:
//  - play while practicing  -> playing from the practice position
//  - practice while playing -> practicing from the playing position
//  - the active button      -> disengage (paused mode, position retained)
//  - a paused mode          -> resumes from its own position
function transportEngagePlay() {
  if (typeof isPracticeActive === "function" && isPracticeActive() && window.OCA_PRACTICE) {
    const pos = Math.max(0, OCA_PRACTICE.posIdx());
    OCA_PRACTICE.stop();
    playMelody(pos);
    return;
  }
  if (typeof isMelodyPlaying === "function" && isMelodyPlaying()) { pauseMelody(); return; }
  if (typeof isMelodyPaused === "function" && isMelodyPaused()) { resumeMelody(); return; }
  playMelody();
}

function transportEngagePractice() {
  if (window.OCA_PRACTICE && (
    (typeof isMelodyPlaying === "function" && isMelodyPlaying()) ||
    (typeof isMelodyPaused === "function" && isMelodyPaused()))) {
    // Swap from playback (or a paused playback) with the melody's position.
    const pos = (typeof liveIdx !== "undefined" && liveIdx >= 0) ? liveIdx : 0;
    OCA_PRACTICE.start(pos);
    return;
  }
  if (typeof isPracticeActive === "function" && isPracticeActive()) { practiceToggle(); return; }
  OCA_PRACTICE.start();
}

function isTextEntry(el) {
  if (!el) return false;
  if (el.isContentEditable) return true;
  const tag = el.tagName;
  if (tag === "TEXTAREA") return true;
  if (tag === "INPUT") {
    const t = (el.type || "text").toLowerCase();
    return !["checkbox","radio","range","button","submit","reset","file","color"].includes(t);
  }
  return false;
}

function wireSpacebar() {
  document.addEventListener("keydown", e => {
    if (e.code !== "Space" && e.key !== " ") return;
    if (e.repeat || e.metaKey || e.ctrlKey || e.altKey) return;
    if (isTextEntry(document.activeElement)) return;
    e.preventDefault();
    unlockAudio();
    if (typeof isPracticeActive === "function" && isPracticeActive()) practiceToggle();
    else if (isFocusMode()) togglePlayPause();
    // Space = Pause/Continue, matching the Play/Pause button everywhere (it
    // used to go through playMelody() and hard-STOPPED a running melody).
    else transportEngagePlay();
  });
}

function canFullscreen(el) {
  // Test hook: ?nofs=1 forces the CSS fallback path (simulates iPhone Safari).
  if (/[?&]nofs=1\b/.test(location.search)) return false;
  return !!(el && (el.requestFullscreen || el.webkitRequestFullscreen));
}

function toggleFullscreen(el) {
  const fsEl = document.fullscreenElement || document.webkitFullscreenElement;
  if (fsEl) {
    const exit = document.exitFullscreen || document.webkitExitFullscreen;
    if (exit) exit.call(document);
  } else if (canFullscreen(el)) {
    (el.requestFullscreen || el.webkitRequestFullscreen).call(el);
  }
}

function isFullscreen() {
  return !!(document.fullscreenElement || document.webkitFullscreenElement)
    || document.body.classList.contains("zen-fallback");
}

function enterZen() {
  // Opening Zen stops any in-flight hover pulse right here (see spawnZenWave).
  stopZenWaves();
  const panel = document.getElementById("tabPanel");
  if (!panel) return;
  if (!isLiveTab()) { zenPrevMode = displayMode; setDisplayMode("single"); }
  if (canFullscreen(panel)) {
    // Let the authoritative fullscreenchange -> sync enable reverb only once
    // fullscreen actually succeeds; enabling here would strand reverb "on" if
    // the request is rejected (no gesture/permission) and no event fires.
    (panel.requestFullscreen || panel.webkitRequestFullscreen).call(panel);
  } else {
    // Fullscreen API unavailable (e.g. Safari on iPhone): use CSS fallback.
    enterFullscreenFallback();
  }
}

// Plain full screen on devices without the Fullscreen API: the same CSS
// fallback as zen, but display-agnostic (no forced single view, no zen UI).
function enterFullscreenFallback() {
  document.body.classList.add("zen-fallback");
  if (window.onZenChange) window.onZenChange();
}

function exitFullscreenFallback() {
  if (!document.body.classList.contains("zen-fallback")) return;
  document.body.classList.remove("zen-fallback");
  if (window.onZenChange) window.onZenChange();
}

function exitZen() {
  // Turn reverb off up front so it can't be stranded if the async
  // fullscreenchange/onZenChange sync is missed or fires out of order.
  if (typeof setReverbEnabled === "function") setReverbEnabled(false);
  // Vibrato/tremolo lives in Zen mode too (same ownership as the reverb).
  if (typeof setVibratoEnabled === "function") setVibratoEnabled(false);
  const fsEl = document.fullscreenElement || document.webkitFullscreenElement;
  if (fsEl) {
    toggleFullscreen();
  } else if (document.body.classList.contains("zen-fallback")) {
    document.body.classList.remove("zen-fallback");
    if (window.onZenChange) window.onZenChange();
  }
}

function toggleZen() {
  if (isFullscreen()) {
    // Already fullscreen but NOT on the zen view (plain Full screen with
    // grid/scroll, or the plain no-API fallback): convert to Zen IN PLACE —
    // keep the fullscreen session, just switch to the single ocarina view.
    // The old behavior called exitZen(), so fullscreen grid/scroll could
    // never reach the zen screen: it merely dropped back to the normal page.
    // Zen focus view re-enabled below; the focus class comes from
    // syncFocusMode (single mode + fullscreen => focus). Exiting stays a
    // toggle: if somehow invoked while already in the zen view, tear down.
    stopZenWaves();
    if (!isLiveTab()) {
      zenPrevMode = displayMode;
      setDisplayMode("single");
      // Nothing changes for the fullscreen machinery, so fullscreenchange
      // never fires — nudge the sync manually (reverb, vibrato, transport).
      if (window.onZenChange) window.onZenChange();
    } else {
      exitZen();
    }
  } else {
    enterZen();
  }
}

// Zen hit-pulse: on hovering the ◎ Zen button, one white ring rolls outward
// and dissolves (css: .zen-wave). A real DOM element, NOT a button pseudo: it
// must paint ABOVE the input/play/piano panel, which the OOT theme stacks at
// z 2 while the tab panel sits at z 1 — nothing inside the panel can ever
// out-paint that. Real fullscreen paints only the fullscreen element's
// subtree, so the wave remounts INSIDE #tabPanel there; otherwise <body>
// tops every panel. The ring keeps flying after unhover; opening Zen stops it.
function spawnZenWave() {
  const fsEl = document.fullscreenElement || document.webkitFullscreenElement;
  const host = fsEl || document.body;
  const btn = document.getElementById("zen");
  if (!btn) return;
  const r = btn.getBoundingClientRect();
  if (!r.width || !r.height) return;
  // Re-entering hover while a pulse is still flying ADDS a new one on top —
  // existing waves always finish their own swell undisturbed.
  const w = document.createElement("div");
  w.className = "zen-wave";
  w.style.left = (r.left + r.width / 2) + "px";
  w.style.top = (r.top + r.height / 2) + "px";
  w.addEventListener("animationend", () => w.remove());
  host.appendChild(w);
}
function stopZenWaves() {
  document.querySelectorAll(".zen-wave").forEach(x => x.remove());
}

// Shareable link for the current view: `?inst=<ocarina id>&song=<library id>
// &zen=1`. Opened anywhere, the app starts on that ocarina with that song
// loaded and straight in the zen view (boot reads the parameters back).
// The hidden `?oot` theme rides along when it is on.
function zenShareUrl() {
  const p = new URLSearchParams();
  const inst = window.CURRENT_INSTRUMENT;
  if (inst && inst.id) p.set("inst", inst.id);
  const sel = document.getElementById("scale");
  if (sel && sel.value) p.set("song", sel.value);
  p.set("zen", "1");
  try { if (new URLSearchParams(location.search).has("oot")) p.set("oot", ""); } catch (e) {}
  const q = p.toString();
  return location.origin + location.pathname + (q ? "?" + q : "");
}

async function copyShareZenLink() {
  const url = zenShareUrl();
  let copied = false;
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(url);
      copied = true;
    }
  } catch (e) {}
  if (!copied) {
    // Clipboard API needs a secure context (localhost or HTTPS); the
    // execCommand route covers http-on-a-LAN setups. Never plain alert() —
    // sandboxed/embedded previews throw. Show the URL so it is still copyable.
    try {
      const ta = document.createElement("textarea");
      ta.value = url;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      copied = document.execCommand("copy");
      ta.remove();
    } catch (e) {}
  }
  if (typeof libToast !== "function") return;
  libToast(copied ? "Zen link copied: " + url : "Auto-copy failed — copy this link: " + url);
}

// Zen entry from a shared link (?zen=1): there is no user gesture yet, so the
// fullscreen request is refused. Catch the rejection and fall through to the
// CSS fallback — the same chrome-less zen view as devices without the
// Fullscreen API. A real fullscreen is still attempted first for the cases
// where it *is* allowed (e.g. an embed with prior activation).
function enterZenFromLink() {
  const panel = document.getElementById("tabPanel");
  if (!panel) return;
  if (!isLiveTab()) { zenPrevMode = displayMode; setDisplayMode("single"); }
  const req = canFullscreen(panel) && (panel.requestFullscreen || panel.webkitRequestFullscreen);
  if (!req) { enterFullscreenFallback(); return; }
  let p = null;
  try { p = req.call(panel); } catch (e) {}
  if (p && typeof p.catch === "function") p.catch(() => enterFullscreenFallback());
  else setTimeout(() => { if (!isFullscreen()) enterFullscreenFallback(); }, 400);
}

function wireZen() {
  const btn = document.getElementById("zen");
  const panel = document.getElementById("tabPanel");
  if (!panel) return;
  window.onZenChange = null;
  if (btn) {
    btn.onclick = () => toggleZen();
    // Hit-pulse: one on every hover entry (continues after unhover; opening
    // Zen stops it in enterZen). Keyboard focus pulses too, but only real
    // keyboard focus (:focus-visible) — a click's focus must not fire one.
    btn.addEventListener("pointerenter", spawnZenWave);
    btn.addEventListener("focus", () => {
      if (btn.matches(":focus-visible")) spawnZenWave();
    });
  }
  const sync = () => {
    if (!isFullscreen() && zenPrevMode) {
      const m = zenPrevMode; zenPrevMode = null; setDisplayMode(m);
    }
    const fsBtn = document.getElementById("fullscreen");
    if (fsBtn) fsBtn.textContent = isFullscreen() ? "Exit full screen" : "Full screen";
    syncFocusMode();
    // Reverb belongs to zen/focus mode, not to any fullscreen: plain full
    // screen with grid/scroll stays dry. Vibrato/tremolo is owned by the
    // same mode — the expressive layer only sounds in Zen.
    if (typeof setReverbEnabled === "function") setReverbEnabled(isFocusMode());
    if (typeof setVibratoEnabled === "function") setVibratoEnabled(isFocusMode());
    // Same ownership as the reverb: the hidden contrabass-support drones
    // (|[C2] bar brackets) only sound in Zen playback; leaving Zen cuts any
    // in-flight drone.
    if (typeof setBassEnabled === "function") setBassEnabled(isFocusMode());
    if (isFullscreen() && isLiveTab() && !isMelodyPlaying()) stopMelody();
  };
  document.addEventListener("fullscreenchange", sync);
  document.addEventListener("webkitfullscreenchange", sync);
  window.onZenChange = sync;
}

// ---------------------------------------------------------------------------
// Performance / headroom dropdown — live audio meters (output peak →
// headroom, limiter gain reduction, clock stalls, active voices) used to
// diagnose phone "clipping" that is really audio-thread starvation (the
// meters themselves live in audio.js: audioPerfSnapshot). The button drops
// the panel in the playback bar; in Zen/focus mode it is moved top-left,
// mirroring the ✕ exit button in the top-right.
let perfWrap = null, perfBtn = null, perfPop = null;
let perfBody = null, perfAct = null;
let perfOpen = false, perfRaf = 0, perfLastRows = -1;

function fmtMs(v) { return v == null ? "—" : (v * 1000).toFixed(1) + " ms"; }
function fmtDb(v) { return v == null ? "—" : (v <= -60 ? "−∞" : v.toFixed(1)); }

function buildPerfWidget() {
  if (perfWrap) return;
  perfWrap = document.createElement("div");
  perfWrap.className = "perf-dd noprint";
  perfBtn = document.createElement("button");
  perfBtn.type = "button";
  perfBtn.id = "perfBtn";
  perfBtn.className = "ghost perf-btn";
  perfBtn.title = "Audio performance — headroom, limiter, stalls";
  perfBtn.setAttribute("aria-haspopup", "true");
  perfBtn.setAttribute("aria-expanded", "false");
  perfBtn.innerHTML = '<span class="perf-ico" aria-hidden="true">∿</span>' +
    '<span class="perf-hr" id="perfHr">perf</span>';
  perfBtn.addEventListener("click", e => {
    e.stopPropagation();
    perfOpen = !perfOpen;
    perfBtn.setAttribute("aria-expanded", perfOpen ? "true" : "false");
    perfPop.hidden = !perfOpen;
    if (perfOpen) {
      if (typeof audioPerfReset === "function") audioPerfReset();
      perfLastRows = -1;
      perfTick(); // synchronous first render — the pop never shows empty
      clampPerfPop();
    } else cancelAnimationFrame(perfRaf);
  });
  perfPop = document.createElement("div");
  perfPop.className = "perf-pop";
  perfPop.hidden = true;
  perfPop.addEventListener("click", e => e.stopPropagation());
  // The rows rebuild every ~180 ms, so the Lite switch lives in its own
  // strip OUTSIDE the rebuilt body — its label/state wouldn't survive the
  // innerHTML swap otherwise. Always available (the point: switch right
  // where you see the problem), accent-highlighted when issues are detected.
  perfBody = document.createElement("div");
  perfBody.className = "perf-body";
  perfAct = document.createElement("div");
  perfAct.className = "perf-act";
  const actBtn = document.createElement("button");
  actBtn.type = "button";
  actBtn.id = "perfActLite";
  // State toggle, same vocabulary as the "Enlarge small holes" button: label
  // stays "Lite", the pressed/engaged look carries the state, and the plain
  // "(enabled)/(disabled)" text after it says what is what.
  actBtn.className = "toggle-btn";
  actBtn.setAttribute("aria-pressed", "false");
  actBtn.title = "Toggle the Lite voice — skips the air/edge/wind/chiff/overtone layers, the wander LFOs and the reverb convolver; cheaper CPU, same pitch and level (not quieter)";
  actBtn.textContent = "Lite";
  actBtn.addEventListener("click", () => {
    const liteCb = document.getElementById("liteMel");
    if (!liteCb) return;
    liteCb.checked = !liteCb.checked;
    liteCb.dispatchEvent(new Event("change")); // persists via the checkbox listener
    // Re-sync from a FRESH snapshot: a stale/absent `s` would drop the
    // "issues detected" accent until the next poll.
    perfSyncAct((typeof audioPerfSnapshot === "function") ? audioPerfSnapshot() : null);
  });
  perfAct.appendChild(actBtn);
  const actState = document.createElement("span");
  actState.className = "perf-act-state";
  actState.id = "perfActState";
  perfAct.appendChild(actState);
  const actTip = document.createElement("span");
  actTip.className = "perf-act-tip";
  perfAct.appendChild(actTip);
  perfPop.appendChild(perfBody);
  perfPop.appendChild(perfAct);
  perfWrap.appendChild(perfBtn);
  perfWrap.appendChild(perfPop);
  document.addEventListener("click", () => {
    if (perfOpen) {
      perfOpen = false;
      perfPop.hidden = true;
      perfBtn.setAttribute("aria-expanded", "false");
      cancelAnimationFrame(perfRaf);
    }
  });
}

// Keep the meters on-screen: on narrow windows the centered pop hangs past a
// viewport edge and drags a horizontal scrollbar along (the user scrolls for
// a screen they never asked for). Shift the pop so it hugs the edge instead.
// Only the inline playback-head placement needs this — Zen's pop is fixed and
// already viewport-anchored.
function clampPerfPop() {
  if (!perfPop || perfPop.hidden || !perfWrap || !perfWrap.offsetParent) return;
  const panel = document.getElementById("tabPanel");
  if (panel && panel.classList.contains("focus")) return; // Zen: own fixed geometry
  perfPop.style.left = ""; // base: left 50% + translateX(-50%)
  const r = perfPop.getBoundingClientRect();
  const pad = 8;
  // innerWidth counts the vertical-scrollbar gutter; clientWidth is the real
  // layout viewport — clamping to innerWidth let the pop poke a few px into
  // the scrollbar and spawn a horizontal scrollbar even with room to slide left.
  const vw = document.documentElement.clientWidth;
  /* one pass keeps both edges legal even on narrow windows */
  const left = Math.min(
    Math.max(r.left, pad),
    Math.max(pad, vw - pad - Math.ceil(r.width))
  );
  const dx = left - r.left;
  if (dx) perfPop.style.left = "calc(50% + " + dx + "px)";
}

function perfTick() {
  if (!perfOpen) return;
  clampPerfPop();
  const s = (typeof audioPerfSnapshot === "function") ? audioPerfSnapshot() : { ok: false };
  perfUpdateBadge(s);
  const now = performance.now();
  if (now - perfLastRows > 180) { perfLastRows = now; perfUpdateRows(s); }
  perfRaf = requestAnimationFrame(perfTick);
}

function perfUpdateBadge(s) {
  const hr = document.getElementById("perfHr");
  if (!hr || !perfBtn) return;
  let cls = "";
  let txt = "—";
  if (s.ok && s.peak > 1e-5) {
    const db = -20 * Math.log10(s.peak); // headroom to 0 dBFS
    txt = db.toFixed(1) + " dB";
    cls = db >= 6 ? "perf-ok" : db >= 3 ? "perf-warn" : "perf-bad";
  } else if (s.ok) txt = "idle";
  else txt = "no ctx";
  hr.textContent = txt;
  hr.className = "perf-hr " + cls;
}

function perfUpdateRows(s) {
  if (!perfBody) return;
  if (!s.ok) {
    perfBody.innerHTML = '<div class="perf-cap">Play a note once so the audio context exists, then reopen.</div>';
    if (perfAct) perfAct.hidden = true;
    return;
  }
  if (perfAct) perfAct.hidden = false;
  const peakDb = s.peak > 1e-5 ? 20 * Math.log10(s.peak) : null;
  const head = peakDb == null ? null : -peakDb;
  const headCls = head == null ? "" : head >= 6 ? "perf-ok" : head >= 3 ? "perf-warn" : "perf-bad";
  const lim = s.limitReduction || 0;
  const row = (k, v, cls) =>
    '<tr><td>' + k + '</td><td' + (cls ? ' class="' + cls + '"' : "") + '>' + v + '</td></tr>';
  const rows = [
    row("Output peak (since open)", peakDb == null ? "silent" : fmtDb(peakDb) + " dBFS"),
    row("Headroom to clipping", head == null ? "—" : fmtDb(head) + " dB", headCls),
    row("Limiter gain reduction", lim <= -0.5 ? fmtDb(lim) + " dB (working)" : "inactive"),
    row("Clock stalls (underruns)", String(s.glitches) + (s.glitches >= 3 ? " ⚠" : "")),
    row("Clock jumps (restarts)", String(s.jumps)),
    row("Active voices (melody)", String(s.voices) + " + " + s.hoverVoices + " hover"),
    row("Sample rate", s.sampleRate + " Hz"),
    row("baseLatency / outputLatency", fmtMs(s.baseLatency) + " / " + fmtMs(s.outputLatency)),
    row("Reverb / voice", (s.reverb ? "on (Zen)" : "off") + " / " + (s.lite ? "Lite" : "full")),
  ];
  perfBody.innerHTML = '<table class="perf-tbl">' + rows.join("") + '</table>' +
    '<p class="perf-cap">Stalls = the audio clock lagged the wall clock — underrun/' +
    'glitches. Headroom &lt; 3 dB risks digital clipping before the limiter. On a slow phone' +
    ' keep Lite on; the full voice runs ~7 biquads + ~10 oscillators per note on top of the' +
    ' always-on reverb convolver.</p>';
  perfSyncAct(s);
}

// Sync the Lite toggle strip from the live state: the button is the toggle
// (engaged look = .toggle-btn.on), the plain "(enabled)/(disabled)" text
// after it states the mode, and the tip carries the issues nudge.
function perfSyncAct(s) {
  if (!perfAct) return;
  const liteCb = document.getElementById("liteMel");
  const btn = perfAct.querySelector("#perfActLite");
  const state = perfAct.querySelector("#perfActState");
  const tip = perfAct.querySelector(".perf-act-tip");
  const on = !!(liteCb && liteCb.checked);
  btn.classList.toggle("on", on);
  btn.setAttribute("aria-pressed", on ? "true" : "false");
  if (state) state.textContent = on ? "(enabled)" : "(disabled)";
  const issues = s && s.ok && (s.glitches > 0 || s.jumps > 0);
  perfAct.classList.toggle("warn", !!(issues && !on));
  if (tip) {
    tip.textContent = issues && !on ? "Issues detected — Lite reduces the CPU load" : "";
  }
}

// Move the widget: fixed top-left in Zen/focus mode (mirrors the ✕), inline
// in the playback bar otherwise.
function perfRelocate() {
  buildPerfWidget();
  const panel = document.getElementById("tabPanel");
  const head = document.querySelector("#playback .box-head");
  const zen = !!(panel && panel.classList.contains("focus"));
  const target = zen ? panel : head;
  if (target && perfWrap.parentElement !== target) target.appendChild(perfWrap);
}

// Collapsible section bodies: INPUT / PLAYBACK have a top-left chevron in
// their box-head so the tall blocks fold away. They start collapsed — expand
// on demand.
function wireCollapsers() {
  ["inputBlock", "playback"].forEach(id => {
    const block = document.getElementById(id);
    const btn = block && block.querySelector(".collapse-btn");
    if (!block || !btn) return;
    const set = c => {
      block.classList.toggle("collapsed", c);
      btn.setAttribute("aria-expanded", c ? "false" : "true");
      btn.title = c ? "Expand" : "Collapse";
      // Re-measure the textarea (fitInput computed it while display:none).
      if (!c && id === "inputBlock" && typeof fitInput === "function") fitInput();
    };
    btn.onclick = () => set(!block.classList.contains("collapsed"));
    set(true); // always start collapsed — expand on demand
  });
}

// Audio-glitch alert: the watchdog in audio.js raises perfAlert() when it
// suspects underruns (repeated clock lag, cumulative drift). The perf button
// pulses red — forced visible even in Zen — and a toast proposes Lite with a
// one-tap switch. Mounted on <body> so it survives focus-mode relocation of
// the playback bar.
let perfToast = null, perfToastTimer = 0;

function wirePerfAlerts() {
  if (typeof setPerfAlertListener === "function") setPerfAlertListener(perfAlert);
}

function perfAlert() {
  buildPerfWidget();
  perfBtn.classList.add("alerted");
  if (perfToast) return; // one toast at a time
  perfToast = document.createElement("div");
  perfToast.className = "glitch-toast noprint" + (isFocusMode() ? " in-zen" : "");
  perfToast.addEventListener("click", e => e.stopPropagation()); // keep a pop opened via "Details" alive — the document click-closer would otherwise kill it in the same bubble
  perfToast.innerHTML =
    '<span class="gt-txt">Audio glitches detected</span>' +
    '<button type="button" class="ghost" id="gtLite">Turn on Lite</button>' +
    '<button type="button" class="ghost" id="gtMore">Details</button>' +
    '<button type="button" class="gt-x" title="Dismiss" aria-label="Dismiss">✕</button>';
  const lite = perfToast.querySelector("#gtLite");
  const liteCb = document.getElementById("liteMel");
  if (liteCb && liteCb.checked) lite.textContent = "Lite already on";
  lite.onclick = () => {
    if (liteCb && !liteCb.checked) {
      liteCb.checked = true;
      liteCb.dispatchEvent(new Event("change")); // persists via the checkbox listener
      lite.textContent = "Lite on";
    }
    perfDismissToast();
  };
  perfToast.querySelector("#gtMore").onclick = () => {
    if (!perfOpen) perfBtn.click(); // open the meters for inspection
    perfDismissToast();
  };
  perfToast.querySelector(".gt-x").onclick = () => perfDismissToast();
  // Mount INSIDE #tabPanel in Zen/focus mode: a body-level toast would be
  // painted over by the fullscreen element and never seen there.
  (isFocusMode() ? document.getElementById("tabPanel") : document.body).appendChild(perfToast);
  perfToastTimer = setTimeout(perfDismissToast, 25000);
}

function perfDismissToast() {
  clearTimeout(perfToastTimer);
  if (perfToast && perfToast.parentElement) perfToast.remove();
  perfToast = null;
  if (perfBtn) perfBtn.classList.remove("alerted");
}
