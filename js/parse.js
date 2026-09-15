function parse(src) {
  const tokens = [];
  const re = /([A-Ga-g])([#b])?(\d)?(\/\d+\.?)?|(\|)|(r)(\/\d+\.?)?|(-)(\/\d+\.?)?|(~)|(#[^\n]*)/g;
  let m, lastOct = 4, lastPitch = null, canTie = false, pendingSlide = false;
  const text = src.replace(/[–—]/g, "|");
  while ((m = re.exec(text))) {
    if (m[11]) continue;
    if (m[10]) { if (lastPitch) pendingSlide = true; continue; }
    if (m[5]) { tokens.push({type:"bar"}); continue; }
    if (m[6]) {
      const pd = parseDur(m[7]);
      tokens.push({type:"rest", dur: pd.dur, dotted: pd.dotted, beats: pd.beats});
      canTie = false;
      pendingSlide = false;
      continue;
    }
    if (m[8]) {
      const pd = parseDur(m[9]);
      const t = {type:"tie", dur: pd.dur, dotted: pd.dotted, beats: pd.beats, raw: m[0], id: ""};
      if (canTie && lastPitch) {
        t.id = lastPitch.id;
        t.spellLetter = lastPitch.spellLetter;
        t.spellAcc = lastPitch.spellAcc;
        t.spellOct = lastPitch.spellOct;
      }
      tokens.push(t);
      pendingSlide = false;
      continue;
    }
    const letter = m[1].toUpperCase();
    const acc = m[2] || "";
    let oct = m[3] ? parseInt(m[3],10) : lastOct;
    const pd = parseDur(m[4]);
    const dur = pd.dur;
    const spellOct = oct;
    lastOct = oct;
    let core = letter;
    if (acc === "#") core += "s";
    else if (acc === "b") {
      const flat = {C:["B",-1], D:["Cs",0], E:["Ds",0], F:["E",0], G:["Fs",0], A:["Gs",0], B:["As",0]};
      const [n, d] = flat[letter];
      core = n; oct += d;
    }
    const tok = {
      type:"note", id: core + oct, dur, dotted: pd.dotted, beats: pd.beats, raw: m[0],
      spellLetter: letter, spellAcc: acc, spellOct
    };
    if (pendingSlide && lastPitch) {
      tok.slide = true;
      tok.slideFrom = lastPitch.id;
    }
    pendingSlide = false;
    tokens.push(tok);
    lastPitch = tok;
    canTie = true;
  }
  return tokens;
}

function parseDur(spec) {
  if (!spec) return { dur: 4, dotted: false, beats: 1 };
  const s = String(spec).replace(/^\//, "");
  const dotted = /\.$/.test(s);
  const dur = parseInt(s, 10) || 4;
  const beats = (4 / dur) * (dotted ? 1.5 : 1);
  return { dur, dotted, beats };
}

function durLabel(d, dotted) {
  d = +d;
  let s = "";
  if (d === 1) s = "\uD834\uDD5D";
  else if (d === 2) s = "\uD834\uDD5E";
  else if (d === 4) s = "\uD834\uDD5F";
  else if (d === 8) s = "\uD834\uDD60";
  else if (d === 16) s = "\uD834\uDD61";
  else s = "1/"+d;
  return dotted ? s + "." : s;
}

function pretty(id) {
  return id.replace(/^([A-G])s(\d)$/, "$1#$2");
}

function octSub(n) {
  return String(n).replace(/[0-9]/g, d => String.fromCharCode(0x2080 + +d));
}

function spelledLabel(t) {
  if (!t || (t.type !== "note" && t.type !== "tie")) return "";
  const letter = t.spellLetter || (t.id && t.id[0]) || "";
  const acc = t.spellAcc === "#" ? "\u266f" : t.spellAcc === "b" ? "\u266d" : "";
  const oct = t.spellOct != null ? t.spellOct : ((String(t.id || "").match(/\d+$/) || [])[0] || "");
  return letter + acc + octSub(oct);
}

function isTempoComment(line) {
  return /^#\s*tempo\s+/i.test(line);
}

function isSwingComment(line) {
  return /^#\s*swing\s+/i.test(line);
}

function tempoFromText(text) {
  const m = String(text).match(/^#\s*tempo\s+(\d+)/im) || String(text).match(/\n#\s*tempo\s+(\d+)/i);
  return m ? +m[1] : null;
}

function swingFromText(text) {
  const m = String(text).match(/^#\s*swing\s+(\d+)/im) || String(text).match(/\n#\s*swing\s+(\d+)/i);
  return m ? +m[1] : null;
}

function titleFromText(text) {
  const line = String(text || "").split("\n").find(l =>
    l.startsWith("#") && !isTempoComment(l) && !isSwingComment(l)
  );
  return line ? line.replace(/^#\s*/, "") : "";
}

function withPlayHeaders(body, name, bpm, swing) {
  const rest = String(body || "").split("\n").filter(l => !isTempoComment(l) && !isSwingComment(l));
  if (name) {
    const title = "# " + String(name).trim();
    if (rest[0] && rest[0].startsWith("#")) rest[0] = title;
    else rest.unshift(title);
  }
  const title = rest[0] && rest[0].startsWith("#") ? [rest.shift()] : [];
  const t = bpm != null ? bpm : 100;
  const s = Math.max(0, +(swing != null ? swing : 0) || 0);
  const head = [...title, "# tempo " + t];
  if (s > 0) head.push("# swing " + s);
  return [...head, ...rest].join("\n").replace(/\n+$/, "\n");
}

function withTempoLine(body, bpm) {
  const swing = swingFromText(body);
  return withPlayHeaders(body, null, bpm, swing != null ? swing : 0);
}

function withTitleAndTempo(body, name, bpm) {
  const swing = swingFromText(body);
  return withPlayHeaders(body, name, bpm, swing != null ? swing : 0);
}
