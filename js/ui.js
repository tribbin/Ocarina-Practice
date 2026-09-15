let APP_CSS = "";
let lastTokens = [];
let liveIdx = -1;
let lastHoverNoteAt = 0;
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
  const parts = [durLabel(tokens[idx].dur, tokens[idx].dotted)];
  for (let i = idx + 1; i < tokens.length; i++) {
    if (tokens[i].type === "bar") continue;
    if (tokens[i].type === "tie") parts.push(durLabel(tokens[i].dur, tokens[i].dotted));
    else break;
  }
  return parts.join("+");
}

function tallyTokens(tokens) {
  const problems = [];
  let notes = 0, outOf = 0, switches = 0, prevCh = null;
  tokens.forEach(t => {
    if (t.type === "bar" || t.type === "rest") return;
    if (t.type === "tie") {
      if (!t.id || !NOTES.includes(t.id)) problems.push((t.raw || "-") + " (nothing to continue)");
      return;
    }
    if (!NOTES.includes(t.id)) {
      problems.push(t.raw + " → " + t.id + " (out of A3–G6)");
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
    const r = document.createElement("div"); r.className = "rest";
    r.style.borderColor = "var(--accent)"; r.style.color = "var(--accent)";
    r.dataset.i = String(i);
    r.textContent = (t.raw || id) + " ✕";
    sheet.appendChild(r);
    return;
  }
  const ch = CHAMBER[id];
  const card = document.createElement("div");
  card.className = "card";
  card.dataset.i = String(i);
  card.innerHTML = `<div class="compact">${ocarinaSVG(COVER[id] || [], ch)}</div>
    <div class="meta"><span class="nm">${spelledLabel(t)}</span>
     <span class="badge ch${ch}">CH ${ch}</span>
     <span class="dur">${durLabel(t.dur, t.dotted)}</span></div>`;
  sheet.appendChild(card);
}

function fillFullSheet(sheet, tokens) {
  sheet.classList.remove("live");
  tokens.forEach((t, i) => {
    if (t.type === "bar") {
      const b = document.createElement("div"); b.className = "tab-bar"; sheet.appendChild(b); return;
    }
    if (t.type === "rest") {
      const r = document.createElement("div"); r.className = "card rest";
      r.dataset.i = String(i);
      r.innerHTML = `<div class="compact">rest</div>
        <div class="meta"><span></span>
        <span class="dur">${durLabel(t.dur, t.dotted)}</span></div>`;
      sheet.appendChild(r); return;
    }
    if (t.type === "tie") {
      if (!t.id || !NOTES.includes(t.id)) {
        const r = document.createElement("div"); r.className = "rest";
        r.style.borderColor = "var(--accent)"; r.style.color = "var(--accent)";
        r.dataset.i = String(i);
        r.textContent = (t.raw || "-") + " ✕"; sheet.appendChild(r); return;
      }
      const r = document.createElement("div"); r.className = "card rest tie";
      r.dataset.i = String(i);
      r.innerHTML = `<div class="compact">–</div>
        <div class="meta"><span class="nm">–</span>
        <span class="dur">${durLabel(t.dur, t.dotted)}</span></div>`;
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
        <span class="dur">${durLabel(t.dur, t.dotted)}</span></div>`;
  }
  const id = t.id;
  if ((t.type === "note" || t.type === "tie") && NOTES.includes(id)) {
    const ch = CHAMBER[id];
    return `<div class="compact">${ocarinaSVG(COVER[id] || [], ch)}</div>
      <div class="meta"><span class="nm">${spelledLabel(t)}</span>
        <span class="badge ch${ch}">CH ${ch}</span>
        <span class="dur">${combinedDurLabel(tokens, i)}</span></div>`;
  }
  return `<div class="compact"></div><div class="meta"><span class="nm">${t.raw || ""} ✕</span></div>`;
}

function fillLiveSheet(sheet, tokens, idx) {
  sheet.classList.remove("scroll");
  sheet.classList.add("live");
  let i = idx;
  if (i == null || i < 0 || !tokens[i] || tokens[i].type === "bar") i = firstSoundIdx(tokens);
  if (!tokens.length || i < 0 || !tokens[i] || tokens[i].type === "bar") return;
  const card = document.createElement("div");
  const t = tokens[i];
  card.className = "card live" + (t.type === "rest" ? " is-rest" : "");
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
}

function render() {
  try {
    const src = document.getElementById("src").value;
    fitInput();
    document.getElementById("title").textContent = titleFromText(src);
    const typedTempo = tempoFromText(src);
    if (typedTempo) applyTempo(typedTempo);
    const typedSwing = swingFromText(src);
    applySwing(typedSwing != null ? typedSwing : 0);
    const tokens = parse(src);
    lastTokens = tokens;
    drawTokens(tokens);
    const sheet = document.getElementById("sheet");
    const err = document.getElementById("err");
    sheet.innerHTML = "";
    const { notes, switches, problems } = tallyTokens(tokens);
    if (isLiveTab()) {
      sheet.classList.remove("scroll");
      fillLiveSheet(sheet, tokens, liveIdx);
    } else {
      sheet.classList.toggle("scroll", isScrollMode());
      fillFullSheet(sheet, tokens);
    }
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
  const el = document.getElementById("tempo");
  const bpm = el ? +el.value : 100;
  return 60 / Math.max(40, Math.min(180, bpm || 100));
}

function tokenSeconds(tokOrDur, dotted) {
  const beats = (tokOrDur && typeof tokOrDur === "object")
    ? (tokOrDur.beats || 1)
    : (4 / (tokOrDur || 4)) * (dotted ? 1.5 : 1);
  return Math.max(0.12, beats * quarterSec());
}

function highlightToken(i, noteId) {
  liveIdx = i;
  document.querySelectorAll(".tok.now, .card.now, .rest.now, .key.now").forEach(el => el.classList.remove("now"));
  document.querySelectorAll('.tok[data-i="' + i + '"]').forEach(el => el.classList.add("now"));
  if (isMelodyPlaying()) scrollFocusStripTo(i);
  if (isLiveTab()) {
    updateLiveTab(lastTokens.length ? lastTokens : parse(document.getElementById("src").value), i);
  } else {
    const card = document.querySelector('.card[data-i="' + i + '"], .rest[data-i="' + i + '"]');
    if (card) {
      card.classList.add("now");
      const sheet = document.getElementById("sheet");
      if (sheet && sheet.classList.contains("scroll")) {
        const wrap = sheet.parentElement;
        const anchor = barAnchorCard(sheet, i) || card;
        if (wrap) {
          const c = anchor.getBoundingClientRect();
          const w = wrap.getBoundingClientRect();
          const inset = 16;
          const delta = c.left - (w.left + inset);
          wrap.scrollTo({ left: Math.max(0, wrap.scrollLeft + delta), behavior: "smooth" });
        }
      }
    }
  }
  if (noteId) {
    document.querySelectorAll('.key[data-note="' + noteId + '"]').forEach(el => el.classList.add("now"));
  }
}

function barStartIndex(tokens, i) {
  let start = 0;
  for (let k = Math.min(i, tokens.length - 1); k >= 0; k--) {
    if (tokens[k] && tokens[k].type === "bar") { start = k + 1; break; }
  }
  while (start < tokens.length && tokens[start] && tokens[start].type === "bar") start++;
  return start;
}

function barAnchorCard(sheet, i) {
  const toks = lastTokens.length ? lastTokens : parse(document.getElementById("src").value);
  const bi = barStartIndex(toks, i);
  return sheet.querySelector('.card[data-i="' + bi + '"], .rest[data-i="' + bi + '"]');
}

function scrollFocusStripTo(i) {
  const strip = document.getElementById("focusTokens");
  if (!strip || !strip.offsetParent) return;
  const el = strip.querySelector('.tok[data-i="' + i + '"]');
  if (!el) return;
  const s = strip.getBoundingClientRect();
  const c = el.getBoundingClientRect();
  const delta = (c.left + c.width / 2) - (s.left + s.width / 2);
  strip.scrollTo({ left: Math.max(0, strip.scrollLeft + delta), behavior: "smooth" });
}

function clearHighlight() {
  document.querySelectorAll(".tok.now, .card.now, .rest.now, .key.now").forEach(el => el.classList.remove("now"));
}

function hoverPreview(i, t) {
  if (isMelodyPlaying() || hoverQuietUntil > Date.now()) return;
  highlightToken(i, t.id);
  unlockAudio();
  if (!audioCtx || audioCtx.state !== "running") return;
  const now = Date.now();
  if (now - lastHoverNoteAt < 70) return;
  lastHoverNoteAt = now;
  playNote(t.id, Math.min(tokenSeconds(t), 0.5));
}

function buildTokenEl(t, i) {
  const el = document.createElement("span");
  el.dataset.i = String(i);
  el.style.cursor = "pointer";
  el.title = "click = play from here";
  if (t.type === "bar") {
    el.className = "tok bar";
    el.textContent = "|";
  } else if (t.type === "rest") {
    el.className = "tok pause";
    el.innerHTML = `r <span class="td">${durLabel(t.dur, t.dotted)}</span>`;
  } else if (t.type === "tie") {
    if (t.id && NOTES.includes(t.id)) {
      el.className = "tok tie ch" + CHAMBER[t.id];
      el.innerHTML = `– <span class="td">${durLabel(t.dur, t.dotted)}</span>`;
      el.addEventListener("mouseenter", () => hoverPreview(i, t));
      el.addEventListener("mouseleave", () => {
        if (!isMelodyPlaying()) clearHighlight();
      });
    } else {
      el.className = "tok bad";
      el.textContent = t.raw || "-";
    }
  } else if (!NOTES.includes(t.id)) {
    el.className = "tok bad";
    el.textContent = t.raw || t.id;
  } else {
    el.className = "tok ch" + CHAMBER[t.id];
    el.innerHTML = `${spelledLabel(t)} <span class="td">${durLabel(t.dur, t.dotted)}</span>`;
    el.addEventListener("mouseenter", () => hoverPreview(i, t));
    el.addEventListener("mouseleave", () => {
      if (!isMelodyPlaying()) clearHighlight();
    });
  }
  el.addEventListener("click", e => { e.preventDefault(); unlockAudio(); playMelody(i); });
  return el;
}

function drawTokenStrip(box, tokens) {
  if (!box) return;
  box.innerHTML = "";
  tokens.forEach((t, i) => box.appendChild(buildTokenEl(t, i)));
}

function drawTokens(tokens) {
  hoverQuietUntil = Date.now() + 400;
  drawTokenStrip(document.getElementById("tokens"), tokens);
  drawTokenStrip(document.getElementById("focusTokens"), tokens);
}

function addNote(id) {
  const ta = document.getElementById("src");
  const needsSpace = ta.value.length && !/\s$/.test(ta.value);
  ta.value += (needsSpace ? " " : "") + pretty(id);
  clearLibrarySelection();
  render();
}

function buildKB() {
  const kb = document.getElementById("kb");
  const whites = ["C","D","E","F","G","A","B"];
  const blackAfter = {C:"Cs", D:"Ds", F:"Fs", G:"Gs", A:"As"};
  for (const oct of [3,4,5,6]) {
    const col = document.createElement("div"); col.className = "oct";
    for (const w of whites) {
      const cell = document.createElement("div"); cell.className = "pkey";
      const id = w + oct;
      const k = document.createElement("div"); k.className = "key";
      if (NOTES.includes(id)) {
        k.dataset.note = id;
        k.title = id + " — click hear, right-click add";
        k.innerHTML = `<span class="n">${w}${oct===4?"":oct}</span>`;
        k.onclick = () => playNote(id);
        k.oncontextmenu = e => { e.preventDefault(); playNote(id); addNote(id); };
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
          b.title = sid + " — click hear, right-click add";
          b.onclick = () => playNote(sid);
          b.oncontextmenu = e => { e.preventDefault(); playNote(sid); addNote(sid); };
        } else {
          b.style.opacity = .2;
        }
        cell.appendChild(b);
      }
      col.appendChild(cell);
    }
    kb.appendChild(col);
  }
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

function printableHtml() {
  const title = document.getElementById("title").textContent || "Bass C Triple tabs";
  const css = pageCss();
  const tmp = document.createElement("div");
  tmp.className = "sheet";
  fillFullSheet(tmp, lastTokens.length ? lastTokens : parse(document.getElementById("src").value));
  const sheet = tmp.innerHTML;
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${title}</title>
<style>${css}
body{background:#fff}
header.app,.panel:first-of-type{display:none}
.wrap{max-width:none;padding:12px}
@media print { @page { margin: 10mm; } }
</style></head>
<body>
<h1 style="font:650 18px/1.3 system-ui;margin:0 0 12px">${title}</h1>
<div id="sheet" class="sheet">${sheet}</div>
</body></html>`;
}

function persistPlayHeaders() {
  const ta = document.getElementById("src");
  if (!ta) return;
  ta.value = withPlayHeaders(ta.value, null, currentTempo(), currentSwing());
  fitInput();
}

function wireUi() {
  document.getElementById("playMel").onclick = playMelody;
  const tempoEl = document.getElementById("tempo");
  if (tempoEl) {
    tempoEl.addEventListener("input", () => {
      applyTempo(+tempoEl.value);
      persistPlayHeaders();
    });
  }
  const focusTempoEl = document.getElementById("focusTempo");
  if (focusTempoEl) {
    focusTempoEl.addEventListener("input", () => {
      applyTempo(+focusTempoEl.value);
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
      alert("Popup blocked — use Download tabs instead.");
    }
  };
  document.getElementById("download").onclick = () => {
    const blob = new Blob([printableHtml()], {type: "text/html"});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "ocarina-tabs.html";
    a.click();
    URL.revokeObjectURL(a.href);
  };
  document.getElementById("clear").onclick = () => {
    document.getElementById("src").value = "";
    clearLibrarySelection();
    resetLiveTab();
    render();
  };
  document.getElementById("src").addEventListener("input", render);
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
  updateModeButtons();
  const fsBtn = document.getElementById("fullscreen");
  if (fsBtn) fsBtn.onclick = () => toggleFullscreen(document.getElementById("tabPanel"));
  document.addEventListener("mousemove", revealZenUi);
  wireZen();
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
  if (pp) pp.onclick = () => { unlockAudio(); togglePlayPause(); };
  if (st) st.onclick = () => stopMelody();
  if (lp) lp.onclick = () => {
    const cb = document.getElementById("loopMel");
    if (cb) cb.checked = !cb.checked;
    syncLoopUI();
  };
  const loopCb = document.getElementById("loopMel");
  if (loopCb) loopCb.addEventListener("change", syncLoopUI);
  if (ex) ex.onclick = () => toggleFullscreen(document.getElementById("tabPanel"));
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
  const fs = !!(document.fullscreenElement || document.webkitFullscreenElement);
  const on = fs && isLiveTab();
  panel.classList.toggle("focus", on);
  if (on) {
    applyTempo(currentTempo());
    syncLoopUI();
    revealZenUi();
    const toks = lastTokens.length ? lastTokens : parse(document.getElementById("src").value);
    scrollFocusStripTo(liveIdx >= 0 ? liveIdx : firstSoundIdx(toks));
  }
}

function updateTransportUI() {
  const playing = typeof isMelodyPlaying === "function" && isMelodyPlaying();
  const main = document.getElementById("playMel");
  if (main) main.textContent = playing ? "Stop" : "Play";
  const fp = document.getElementById("focusPlay");
  if (fp) {
    fp.textContent = playing ? "\u23F8" : "\u25B6";
    fp.classList.toggle("is-playing", playing);
  }
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
    if (isFocusMode()) togglePlayPause();
    else playMelody();
  });
}

function toggleFullscreen(el) {
  const fsEl = document.fullscreenElement || document.webkitFullscreenElement;
  if (fsEl) {
    (document.exitFullscreen || document.webkitExitFullscreen).call(document);
  } else if (el) {
    (el.requestFullscreen || el.webkitRequestFullscreen).call(el);
  }
}

function isFullscreen() {
  return !!(document.fullscreenElement || document.webkitFullscreenElement);
}

function enterZen() {
  const panel = document.getElementById("tabPanel");
  if (!panel) return;
  if (!isLiveTab()) { zenPrevMode = displayMode; setDisplayMode("single"); }
  (panel.requestFullscreen || panel.webkitRequestFullscreen).call(panel);
}

function wireZen() {
  const btn = document.getElementById("zen");
  const panel = document.getElementById("tabPanel");
  if (!panel) return;
  if (btn) btn.onclick = () => { if (isFullscreen()) toggleFullscreen(); else enterZen(); };
  const sync = () => {
    if (!isFullscreen() && zenPrevMode) {
      const m = zenPrevMode; zenPrevMode = null; setDisplayMode(m);
    }
    const fsBtn = document.getElementById("fullscreen");
    if (fsBtn) fsBtn.textContent = isFullscreen() ? "Exit full screen" : "Full screen";
    syncFocusMode();
    if (isFullscreen() && isLiveTab() && !isMelodyPlaying()) stopMelody();
  };
  document.addEventListener("fullscreenchange", sync);
  document.addEventListener("webkitfullscreenchange", sync);
}
