function parse(src) {
  const tokens = [];
  const re = /([A-Ga-g])([#b])?(\d)?(?!\d)(\/\d+\.?t?)?(!)?|(\|)\s*(\[[^\]]*\])?|(r)(\/\d+\.?t?)?|(-)(\/\d+\.?t?)?|(~)|(#[^\n]*)|(\[[^\]]*\])/g;
  let m, lastOct = 4, lastPitch = null, canTie = false, pendingSlide = false;
  // Staccato may be written before or after the duration: normalize
  // "C5!/8" -> "C5/8!" so the /8 always parses (the note regex consumes
  // dur-then-bang only).
  const text = src.replace(/[–—]/g, "|").replace(/!(\/\d+\.?t?)/g, "$1!");
  while ((m = re.exec(text))) {
    if (m[13]) {
      // Inline "# tempo N" AFTER music has started emits a tempo-change token so
      // playback shifts tempo from this point on. Leading "# tempo" lines are
      // the header/default (handled globally) and are not tokenized. Other
      // comments are ignored.
      const tc = m[13].match(/^#\s*tempo\s+(\d+)/i);
      if (tc && tokens.length) tokens.push({ type: "tempo", bpm: +tc[1] });
      if (tc) {
        // "# tempo N" written mid-line must NOT swallow the rest of the line
        // (the comment match runs to \n). Rewind the scanner to just past
        // the tempo number so trailing notes/tempo survive; every other
        // comment keeps its whole-line swallow.
        re.lastIndex -= (m[13].length - tc[0].length);
      }
      continue;
    }
    if (m[14]) {
      // Bracket marker NOT welded to a bar line: anywhere between bars it is
      // a hidden support note. Content is the same grammar a bar bracket
      // accepts ("C2", "C2/4.", "~F/4", "-/2", '"Name",C2/2'); a content
      // without a pitch tokenizes to nothing.
      const c = bracketContent(m[14].slice(1, -1));
      if (c) {
        const tok = { type: "bass" };
        if (c.ext != null) {
          tok.ext = c.ext; // [-/2]: extends the pending support's ring
        } else {
          tok.id = c.bass;
          tok.dur = c.dur;
          tok.dotted = c.dotted;
          tok.triplet = c.triplet;
          tok.beats = c.beats;
          if (c.name) tok.desc = c.name; // hidden, but round-trips for tests
          if (c.glide) tok.slide = true; // [~F/4]: slides from the last support
        }
        tokens.push(tok);
      }
      continue;
    }
    if (m[12]) { if (lastPitch) pendingSlide = true; continue; }
    if (m[6]) {
      // Bar line with an optional bracket field, three spoken shapes:
      //   |[C2]            hidden support note for this bar
      //   |["Opening",C2]  named section bar that ALSO carries a support note
      //   |["35th bar from midi"]  plain description (quotes/commas fine)
      //   With a duration the support sounds that long instead of the whole
      //   measure: |["Opening",C2/2] / |[C2/4.]
      const bar = { type: "bar" };
      if (m[7]) {
        const c = bracketContent(m[7].slice(1, -1));
        if (c && c.bass) {
          bar.bass = c.bass;
          bar.beats = c.beats;
          if (c.glide) bar.slide = true;
          if (c.name) bar.desc = c.name;
        } else if (c && c.ext != null) {
          // `| [-/1]` opens a measure: that bracket is NOT bar content — it is
          // a continuation of the PREVIOUS measure's support ring. Emit it as
          // its own marker token (the bar branch would otherwise swallow it).
          tokens.push({ type: "bass", ext: c.ext });
        } else {
          bar.desc = m[7].slice(1, -1).replace(/^["']|["']$/g, "");
        }
        if (!bar.desc) delete bar.desc;
      }
      tokens.push(bar);
      continue;
    }
    if (m[8]) {
      const pd = parseDur(m[9]);
      tokens.push({type:"rest", dur: pd.dur, dotted: pd.dotted, triplet: pd.triplet, beats: pd.beats});
      canTie = false;
      pendingSlide = false;
      continue;
    }
    if (m[10]) {
      const pd = parseDur(m[11]);
      if (canTie && lastPitch) {
        // Continuation of previous note.
        const t = {type:"tie", dur: pd.dur, dotted: pd.dotted, triplet: pd.triplet, beats: pd.beats, raw: m[0], id: lastPitch.id};
        t.spellLetter = lastPitch.spellLetter;
        t.spellAcc = lastPitch.spellAcc;
        t.spellOct = lastPitch.spellOct;
        tokens.push(t);
      } else {
        // Continuation of previous rest (or leading gap): extend as a rest.
        tokens.push({type:"rest", dur: pd.dur, dotted: pd.dotted, triplet: pd.triplet, beats: pd.beats, raw: m[0]});
      }
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
      type:"note", id: core + oct, dur, dotted: pd.dotted, triplet: pd.triplet, beats: pd.beats, raw: m[0],
      spellLetter: letter, spellAcc: acc, spellOct
    };
    if (m[5]) tok.staccato = true;
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
  if (!spec) return { dur: 4, dotted: false, triplet: false, beats: 1 };
  const s = String(spec).replace(/^\//, "");
  const triplet = /t$/.test(s);
  const dotted = /\.t?$/.test(s);
  const dur = parseInt(s, 10) || 4;
  // Triplet = three in the space of two, so each note is 2/3 of its value.
  const beats = (4 / dur) * (dotted ? 1.5 : 1) * (triplet ? 2 / 3 : 1);
  return { dur, dotted, triplet, beats };
}

// Shared bracket-field grammar for bar brackets (|[C2]) and inline markers
// ([C2]): the LAST comma part is either
//   a pitch with optional duration  — C2, C2/4. (no staccato: a drone ring is
//                                     just a length; triplets allowed),
//   a glide into a pitch            — ~F/4 or ~F/2.B (slides from the
//                                     previous support note's pitch),
//   an extension                    — -/2 extends the pending support's ring
//                                     by that many beats (bare - with no
//                                     length means nothing).
// Anything else is not a support note: callers fall back to desc-only and
// silent-skip respectively, so old descriptions never break.
function bracketContent(content) {
  const parts = String(content).split(",");
  const tail = parts[parts.length - 1].trim();
  const meta = parts.length > 1
    ? parts.slice(0, -1).join(",").trim().replace(/^["']|["']$/g, "")
    : null;
  // Extension: dash + optional duration.
  const ext = tail.match(/^-(\/\d+\.?t?)?$/);
  if (ext) {
    if (!ext[1]) return null; // bare [-]: no length, not a support note
    return { ext: parseDur(ext[1]).beats };
  }
  // Glide: ~ Pitch with optional duration.
  const gl = tail.match(/^~\s*([A-G]s?[1-8])(.*)$/);
  if (gl) {
    const rest = gl[2].trim();
    let pd = null;
    if (rest) {
      if (!/^\/\d+\.?t?$/.test(rest)) return null; // junk tail → not a support note
      pd = parseDur(rest);
    }
    const out = {
      bass: gl[1],
      dur: pd ? pd.dur : null,
      dotted: pd ? pd.dotted : false,
      triplet: pd ? pd.triplet : false,
      beats: pd ? pd.beats : null, // null = ring until the next bar (default)
      glide: true,
    };
    if (meta) out.name = meta;
    return out;
  }
  // Plain pitch with optional duration.
  const pm = tail.match(/^([A-G]s?[1-8])(.*)$/);
  if (!pm) return null;
  const rest = pm[2].trim();
  let pd = null;
  if (rest) {
    if (!/^\/\d+\.?t?$/.test(rest)) return null; // junk tail → not a support note
    pd = parseDur(rest);
  }
  const out = {
    bass: pm[1],
    dur: pd ? pd.dur : null,
    dotted: pd ? pd.dotted : false,
    triplet: pd ? pd.triplet : false,
    beats: pd ? pd.beats : null,
  };
  if (meta) out.name = meta;
  return out;
}

function durLabel(d, dotted, triplet) {
  d = +d;
  let s = "";
  if (d === 1) s = "\uD834\uDD5D";
  else if (d === 2) s = "\uD834\uDD5E";
  else if (d === 4) s = "\uD834\uDD5F";
  else if (d === 8) s = "\uD834\uDD60";
  else if (d === 16) s = "\uD834\uDD61";
  else s = "1/"+d;
  if (dotted) s += ".";
  if (triplet) s += "\u00B3"; // superscript 3 = triplet
  return s;
}

function pretty(id) {
  return id.replace(/^([A-G])s(\d)$/, "$1#$2");
}

function midiOf(id) {
  const m = String(id || "").match(/^([A-G]s?)(-?\d)$/);
  if (!m) return null;
  const semi = {C:0,Cs:1,D:2,Ds:3,E:4,F:5,Fs:6,G:7,Gs:8,A:9,As:10,B:11};
  if (!(m[1] in semi)) return null;
  return semi[m[1]] + (+m[2] + 1) * 12;
}

// Returns "below", "above", or "in" for a note id against the current
// instrument's range (from FING.range). Returns null if range unknown.
function rangeCheck(id) {
  const r = (typeof FING !== "undefined" && FING) ? FING.range : null;
  if (!r) return null;
  const n = midiOf(id), lo = midiOf(r.low), hi = midiOf(r.high);
  if (n == null || lo == null || hi == null) return null;
  if (n < lo) return "below";
  if (n > hi) return "above";
  return "in";
}

// True only for a properly-formed pitch that is simply outside the range.
function isOutOfRange(id) {
  const rc = rangeCheck(id);
  return rc === "below" || rc === "above";
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
  // Split off the LEADING header block (title/tempo/swing comment lines at the
  // very top) from the musical body. Tempo/swing lines that appear later in the
  // body are inline changes and must be preserved.
  const lines = String(body || "").split("\n");
  let h = 0;
  while (h < lines.length && lines[h].trim().startsWith("#")) h++;
  const headerLines = lines.slice(0, h);
  const rest = lines.slice(h);
  // Keep any non-tempo/non-swing header comment (e.g. the title) from the top.
  const title = [];
  if (name) {
    title.push("# " + String(name).trim());
  } else {
    const t0 = headerLines.find(l => !isTempoComment(l) && !isSwingComment(l));
    if (t0) title.push(t0);
  }
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
