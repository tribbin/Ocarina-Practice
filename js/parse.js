// Flat spellings re-spell into the s-spelled chart id space (Db4 -> Cs4,
// Cb4 -> B3); #, s and b are all accepted and normalized. Shared by the
// melody branch and the support-bracket grammar so both spellings reach the
// same id — a flat must never silently vanish just because it stood inside
// a bracket.
const FLAT_CORE = { C: ["B", -1], D: ["Cs", 0], E: ["Ds", 0], F: ["E", 0],
                    G: ["Fs", 0], A: ["Gs", 0], B: ["As", 0] };

function coreIdOf(letter, acc, oct) {
  if (acc === "b") {
    const [n, d] = FLAT_CORE[letter];
    return n + (oct + d);
  }
  let core = letter;
  if (acc === "#" || acc === "s") core += "s";
  return core + oct;
}

function parse(src) {
  // Multi-track pre-pass: a body may carry parallel track blocks after the
  // melody ("#track bass audible" / "#track X zen" header lines). parse()
  // stays the MELODY stream's front door (every consumer — render, library,
  // playback — keeps reading a flat melody array), so the blocks' text is
  // lifted away here and parsed separately through parseTracks().
  const split = trackStreamLines(String(src == null ? "" : src));
  const tokens = [];
  const re = /([A-Ga-g])([#bs])?(\d)?(?!\d)(\/\d+\.?t?)?(!)?|(\|)\s*(\[[^\]]*\])?|(r)(\/\d+\.?t?)?|(-)(\/\d+\.?t?)?|(~)|(#[^\n]*)|(\[[^\]]*\])/g;
  let m, lastOct = 4, lastPitch = null, canTie = false, pendingSlide = false;
  // Staccato may be written before or after the duration: normalize
  // "C5!/8" -> "C5/8!" so the /8 always parses (the note regex consumes
  // dur-then-bang only).
  const text = split.melody.join("\n").replace(/[–—]/g, "|")
                 .replace(/!(\/\d+\.?t?)/g, "$1!");
  // Everything the grammar cannot consume becomes a visible "bad" chip
  // instead of silently vanishing (typos, multi-digit octaves like C10,
  // foreign words). Whitespace separators are legal; stray LETTERS are not
  // junk — they are legal octaveless notes by design ("buck" plays something).
  let scanPos = 0;
  const pushJunk = (chunk) => {
    const raw = String(chunk).trim();
    if (raw) tokens.push({ type: "bad", raw });
  };
  while ((m = re.exec(text))) {
    if (m.index > scanPos) pushJunk(text.slice(scanPos, m.index));
    // The inline-tempo rewind below can move the resume point BACK before
    // this match's end — slice() with start > end is "", so no phantom junk.
    scanPos = m.index + m[0].length;
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
        // Orphan tie: no note to continue (start of text, or after a rest).
        // Rests are written with `r` and only `r` — a bare dash is a typo,
        // so surface it as a visible bad chip instead of silently acting
        // as a rest. (Bar-crossing ties keep working: bars don't reset
        // canTie, and every shipped song relies on that.)
        pushJunk(m[0]);
      }
      pendingSlide = false;
      continue;
    }
    const letter = m[1].toUpperCase();
    let acc = m[2] || "";
    let oct = m[3] ? parseInt(m[3],10) : lastOct;
    const pd = parseDur(m[4]);
    const dur = pd.dur;
    const spellOct = oct;
    lastOct = oct;
    const core = coreIdOf(letter, acc, oct);
    // s-spelling is for convenience (canonical ids); display wants the hash.
    if (acc === "s") acc = "#";
    const tok = {
      type:"note", id: core, dur, dotted: pd.dotted, triplet: pd.triplet, beats: pd.beats, raw: m[0],
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
  if (scanPos < text.length) pushJunk(text.slice(scanPos));
  // Invalid "#track" headers (bare header, unknown zone word, extra fields)
  // open nothing and change no stream boundary — their lines stay where they
  // were (a typo'd header's notes keep riding whatever stream was open) and
  // the offending line occurs as a visible bad chip at the stream's end.
  for (const badLine of split.melodyBads) tokens.push({ type: "bad", raw: badLine });
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

// ---------------------------------------------------------------------------
// Multi-track heads (parallel-line serialization decision, 2026-09-26):
// "#track <name> [zen|audible]" opens a real second token stream in the
// body text. The header is line-anchored, case-insensitive; a bare or
// malformed header never splits anything — it only chips (bad-chip
// philosophy: nothing unparsable may silently vanish). Valid headers split
// melody/track and track/track at that line; same-name blocks append into
// ONE stream (a bass written in two halves stays one line).
// ---------------------------------------------------------------------------
const TRACK_HEADER_RE = /^#[ \t]*track\b[ \t]*(.*?)[ \t]*$/i;
const TRACK_NAME_RE = /^[A-Za-z][A-Za-z0-9_-]*$/;

// Line-based pre-pass shared by parse() and parseTracks(): melody lines and
// per-track line buffers. Invalid headers contribute to the owning stream's
// bads and change NO stream boundary (their following lines stay put).
function trackStreamLines(src) {
  const lines = String(src == null ? "" : src).split("\n");
  const melody = [], melodyBads = [], blocks = [];
  const byName = new Map();
  let block = null; // current open track block, or null = melody stream open
  for (const line of lines) {
    const m = TRACK_HEADER_RE.exec(line);
    if (!m) { (block ? block.lines : melody).push(line); continue; }
    const fields = (m[1] || "").split(/\s+/).filter(Boolean);
    const name = fields[0] || "";
    const zone = fields[1] || "audible";
    const valid = TRACK_NAME_RE.test(name) &&
                  (zone === "audible" || zone === "zen") &&
                  fields.length <= 2;
    if (!valid) {
      (block ? block.bads : melodyBads).push(line);
      continue;
    }
    const lower = name.toLowerCase();
    if (byName.has(lower)) {
      // Same name again: CONTINUE that stream (append) instead of opening a
      // second one; the newest zone word wins for it.
      block = byName.get(lower);
      block.zone = zone;
      continue;
    }
    block = { name: lower, zone, lines: [], bads: [] };
    byName.set(lower, block);
    blocks.push(block);
  }
  return { melody, melodyBads, blocks };
}

// Chip shell for a support marker that got written inside a track block:
// support markers are melody-stream syntax (inline `[C2]`, bar `|[Ab2]`,
// extensions `[-/2]`) and a track stream must surface them, never silently
// carry a hidden drone the melody never asked for.
function trackSupportChip(tok) {
  if (tok.ext != null) return { type: "bad", raw: "[-/…]" };
  if (tok.id) return { type: "bad", raw: "[" + (tok.glide ? "~" : "") + pretty(tok.id) + "]" };
  return { type: "bad", raw: "[...]" };
}

// One flat melody array per track, in header order:
// [{ name, zone, tokens }] — each block parses with the same grammar, and a
// block's collected bad headers ride its own stream's tail.
function parseTracks(src) {
  const split = trackStreamLines(src);
  return split.blocks.map(b => {
    const tokens = [];
    for (const tok of parse(b.lines.join("\n"))) {
      if (tok.type === "bass") { tokens.push(trackSupportChip(tok)); continue; }
      if (tok.type === "bar" && tok.bass) {
        const chip = trackSupportChip({ id: tok.bass, glide: tok.slide });
        delete tok.bass; delete tok.beats; delete tok.slide;
        tokens.push(tok);
        tokens.push(chip);
        continue;
      }
      tokens.push(tok);
    }
    for (const badLine of b.bads) tokens.push({ type: "bad", raw: badLine });
    return { name: b.name, zone: b.zone, tokens };
  });
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
// Pitch spellings accept #, s and b like melody notes do; everything
// canonicalizes to the s-spelled chart id (Ab2 -> Gs2, Db2/4. -> Cs2/4.,
// Cb3 -> B2) through the melody branch's own flat table, so a flat inside a
// bracket reaches the same drone a sharp would. Anything else is not a
// support note: callers fall back to desc-only and silent-skip respectively,
// so old descriptions never break.
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
  const gl = tail.match(/^~\s*([A-G])([#sb]?)([1-8])(.*)$/);
  if (gl) {
    const rest = gl[4].trim();
    let pd = null;
    if (rest) {
      if (!/^\/\d+\.?t?$/.test(rest)) return null; // junk tail → not a support note
      pd = parseDur(rest);
    }
    const out = {
      bass: coreIdOf(gl[1], gl[2], +gl[3]),
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
  const pm = tail.match(/^([A-G])([#sb]?)([1-8])(.*)$/);
  if (!pm) return null;
  const rest = pm[4].trim();
  let pd = null;
  if (rest) {
    if (!/^\/\d+\.?t?$/.test(rest)) return null; // junk tail → not a support note
    pd = parseDur(rest);
  }
  const out = {
    bass: coreIdOf(pm[1], pm[2], +pm[3]),
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

export { durLabel, isOutOfRange, octSub, parse, parseTracks, pretty, rangeCheck,
         spelledLabel, midiOf, swingFromText, tempoFromText, titleFromText,
         withPlayHeaders, withTempoLine, withTitleAndTempo };

// Classic-script compat surface (tests + dev console call these by global).
window.parse = parse; window.titleFromText = titleFromText; window.pretty = pretty;
window.parseTracks = parseTracks;
window.tempoFromText = tempoFromText; window.swingFromText = swingFromText;
window.durLabel = durLabel; window.withPlayHeaders = withPlayHeaders;
window.midiOf = midiOf; window.octSub = octSub;
window.spelledLabel = spelledLabel;
window.withTempoLine = withTempoLine;
window.withTitleAndTempo = withTitleAndTempo;
window.rangeCheck = rangeCheck; window.isOutOfRange = isOutOfRange;
