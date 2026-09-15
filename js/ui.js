let APP_CSS = "";

function fitInput() {
  const ta = document.getElementById("src");
  if (!ta) return;
  ta.style.height = "auto";
  ta.style.height = Math.max(74, ta.scrollHeight) + "px";
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
    drawTokens(tokens);
    const sheet = document.getElementById("sheet");
    const err = document.getElementById("err");
    sheet.innerHTML = "";
    const problems = [];
    let notes = 0, outOf = 0, switches = 0, prevCh = null;
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
          problems.push((t.raw || "-") + " (nothing to continue)");
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
      const id = t.id;
      if (!NOTES.includes(id)) {
        problems.push(t.raw + " → " + id + " (out of A3–G6)");
        outOf++;
        const r = document.createElement("div"); r.className = "rest";
        r.style.borderColor = "var(--accent)"; r.style.color = "var(--accent)";
        r.dataset.i = String(i);
        r.textContent = (t.raw || id) + " ✕"; sheet.appendChild(r); return;
      }
      notes++;
      const ch = CHAMBER[id];
      if (prevCh && ch !== prevCh) switches++;
      prevCh = ch;
      const card = document.createElement("div");
      card.className = "card";
      card.dataset.i = String(i);
      const compact = `<div class="compact">${ocarinaSVG(COVER[id] || [], ch)}</div>`;
      card.innerHTML = compact +
        `<div class="meta"><span class="nm">${spelledLabel(t)}</span>
         <span class="badge ch${ch}">CH ${ch}</span>
         <span class="dur">${durLabel(t.dur, t.dotted)}</span></div>`;
      sheet.appendChild(card);
    });
    err.textContent = problems.join(" · ");
    document.getElementById("stats").textContent =
      notes ? `${notes} notes · ${switches} chamber switch${switches===1?"":"es"}` : "Type or click a melody.";
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
  document.querySelectorAll(".tok.now, .card.now, .rest.now, .key.now").forEach(el => el.classList.remove("now"));
  const tok = document.querySelector('.tok[data-i="' + i + '"]');
  if (tok) tok.classList.add("now");
  const card = document.querySelector('.card[data-i="' + i + '"], .rest[data-i="' + i + '"]');
  if (card) {
    card.classList.add("now");
    const sheet = document.getElementById("sheet");
    if (sheet && sheet.classList.contains("scroll")) {
      const wrap = sheet.parentElement;
      if (wrap) {
        const c = card.getBoundingClientRect();
        const w = wrap.getBoundingClientRect();
        const inset = 16;
        const delta = c.left - (w.left + inset);
        wrap.scrollTo({ left: Math.max(0, wrap.scrollLeft + delta), behavior: "smooth" });
      }
    }
  }
  if (noteId) {
    document.querySelectorAll('.key[data-note="' + noteId + '"]').forEach(el => el.classList.add("now"));
  }
}

function clearHighlight() {
  document.querySelectorAll(".tok.now, .card.now, .rest.now, .key.now").forEach(el => el.classList.remove("now"));
}

function drawTokens(tokens) {
  hoverQuietUntil = Date.now() + 400;
  const box = document.getElementById("tokens");
  if (!box) return;
  box.innerHTML = "";
  tokens.forEach((t, i) => {
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
        el.addEventListener("mouseenter", () => {
          if (isMelodyPlaying() || hoverQuietUntil > Date.now()) return;
          highlightToken(i, t.id);
          if (!audioCtx || audioCtx.state !== "running") return;
          playNote(t.id, tokenSeconds(t));
        });
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
      el.addEventListener("mouseenter", () => {
        if (isMelodyPlaying() || hoverQuietUntil > Date.now()) return;
        highlightToken(i, t.id);
        if (!audioCtx || audioCtx.state !== "running") return;
        playNote(t.id, tokenSeconds(t));
      });
      el.addEventListener("mouseleave", () => {
        if (!isMelodyPlaying()) clearHighlight();
      });
    }
    el.addEventListener("click", e => { e.preventDefault(); unlockAudio(); playMelody(i); });
    box.appendChild(el);
  });
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
  const sheet = document.getElementById("sheet").innerHTML;
  const title = document.getElementById("title").textContent || "Bass C Triple tabs";
  const css = pageCss();
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

function wireUi() {
  document.getElementById("playMel").onclick = playMelody;
  function writePlayHeaders() {
    const ta = document.getElementById("src");
    if (!ta) return;
    ta.value = withPlayHeaders(ta.value, null, currentTempo(), currentSwing());
    fitInput();
  }
  const tempoEl = document.getElementById("tempo");
  const tempoVal = document.getElementById("tempoVal");
  if (tempoEl && tempoVal) {
    tempoEl.addEventListener("input", () => {
      tempoVal.textContent = tempoEl.value;
      writePlayHeaders();
    });
  }
  const swingEl = document.getElementById("swing");
  const swingVal = document.getElementById("swingVal");
  if (swingEl && swingVal) {
    swingEl.addEventListener("input", () => {
      swingVal.textContent = swingEl.value;
      writePlayHeaders();
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
    render();
  };
  document.getElementById("src").addEventListener("input", render);
  document.getElementById("bigSmall").onchange = render;
  document.getElementById("scrollTabs").onchange = () => {
    document.getElementById("sheet").classList.toggle("scroll", document.getElementById("scrollTabs").checked);
  };
}
