// Transpose a song body in songs.json by a fixed interval and (optionally) add
// it as a new entry. Verifies the result with js/parse.js and a fingering chart.
//
// Usage (repo root):
//   node skills/song-transposing/scripts/transpose.cjs <srcKey> <shift> [dstKey name group chart.json] [--dry]
//
// Learned-trap-proof by construction:
// - js/parse.js is an ES module (export statement at the end) while this is a
//   CJS tool: export lines are stripped before eval and the required names are
//   asserted afterwards, so the module migration cannot silently starve us.
// - parseInt(o,10): the octave digit arrives as a string; (o+1) would concatenate ("4" -> "41").
// - The s accent (Cs4) is grammar since it was accepted as melody text; the
//   rewrite below consumes it and re-spells from MIDI into the sharp system.
// - Chroma is NOT pre-modded: Cb6 is MIDI 83 (B5), B#5 is MIDI 84 (C6); the octave
//   must carry across letter boundaries, then the result is re-spelled from MIDI.
// - EVERY [...]-bracket (section labels, bar supports | [C2] / | ["x", C2],
//   inline supports [C2/4.] / [-/2] / [~F2/4]) is masked with sentinels and kept
//   VERBATIM: supports are instrument-pinned chambers, never transposed melody.
//   (The bar-label mask used to be the only one; inline supports got their pitch
//   shifted — C2 became A1, a chamber id nothing can resolve. Fixed by masking
//   all bracket spans.) Dropping brackets keeps the broken-label hazard from the
//   label era: parser reads label letters as stray notes (lowercase e/g notes
//   appeared uninvited before the mask fix).
// - "# ..." lines are left untouched.
// - A new entry inherits every source field (tempo, tick, swing, hidden, ...)
//   and overrides name/group/body only — clones of a WIP stay WIP.
const fs = require("fs");

const NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const PC = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
const midiOfTok = t => { // duplicate-free name: parse.js defines its own midiOf
  const m = /^([A-G])(s|b)?(\d+)$/.exec(t.id);
  if (!m) return null;
  let pc = PC[m[1]];
  if (m[2] === "s") pc++; else if (m[2] === "b") pc--;
  return (parseInt(m[3], 10) + 1) * 12 + pc;
};

function loadParse() {
  // Drop export statements (single- or multi-line) from the ES-module source;
  // anything between "export" and the closing brace flies with them.
  const skip = (() => { let on = false; return l => {
    if (on) { on = !/\}/.test(l); return true; }
    on = /^\s*export\b/.test(l);
    return on;
  }; })();
  // Prepend a window shim: parse.js (post-migration) publishes its page-facing
  // surface through a windowed compat block, and reading window.parse keeps us
  // independent of how each name is declared (const stays trapped in the eval's
  // lexical scope, function declarations leak to global — the shim catches both).
  const shims = 'var window = (typeof window !== "undefined") ? window : {};\n';
  (0, eval)(shims + fs.readFileSync("js/parse.js", "utf8")
    .split("\n").filter(l => !skip(l)).join("\n"));
  const w = eval("window");
  if (!w || typeof w.parse !== "function")
    throw new Error("js/parse.js exposes no windowed parse (compat block) — " +
                    "update this loader to its current surface");
  return w.parse;
}

function transpose(source, shift) {
  return source.split("\n").map(line => {
    if (/^\s*#/.test(line)) return line;
    // Stash bracket spans wholesale: sentinel chars AROUND the brackets are not
    // enough — the rewrite regex would still reach a pitch token inside (the
    // old bar-label mask did exactly that and only survived because plain-text
    // labels rarely look like notes). Index-keyed sentinels restore exactly.
    const stash = [];
    line = line.replace(/\[[^\]]*\]/g, m => {
      stash.push(m);
      return "\u0001" + (stash.length - 1) + "\u0001";
    });
    line = line.replace(/([A-G])([#bs]?)(\d)/g, (m, L, acc, o) => {
      const accN = acc === "#" || acc === "s" ? 1 : acc === "b" ? -1 : 0;
      const midi = (parseInt(o, 10) + 1) * 12 + PC[L] + accN + shift;
      return NAMES[((midi % 12) + 12) % 12] + (Math.floor(midi / 12) - 1);
    });
    return line.replace(/\u0001(\d+)\u0001/g, (m, i) => stash[+i]);
  }).join("\n");
}

function main() {
  const argv = process.argv.slice(2);
  const dry = argv.includes("--dry");
  const pos = argv.filter(a => a !== "--dry");
  const [srcKey, shiftArg, dstKey, name, group, chartPath] = pos;
  if (!srcKey || !shiftArg) {
    console.error("usage: node transpose.cjs <srcKey> <shift> [dstKey name group chart.json] [--dry]");
    process.exit(2);
  }
  const shift = parseInt(shiftArg, 10);
  const songs = JSON.parse(fs.readFileSync("songs.json", "utf8"));
  const src = songs[srcKey];
  if (!src) throw new Error("no song '" + srcKey + "' in songs.json");

  const parse = loadParse();
  const srcNotes = parse(src.body).filter(t => t.type === "note");
  const dstBody = transpose(src.body, shift);
  const dstNotes = parse(dstBody).filter(t => t.type === "note");
  const bad = parse(dstBody).filter(t => t.type === "bad");
  if (bad.length)
    throw new Error("transposed body produced bad chips: " +
                    bad.map(t => t.raw).join(", "));

  const srcM = srcNotes.map(midiOfTok), dstM = dstNotes.map(midiOfTok);
  if (srcNotes.length !== dstNotes.length)
    throw new Error("note count changed: " + srcNotes.length + " -> " + dstNotes.length + " (untransposed note or broken label?)");
  const exact = srcM.every((m, i) => m + shift === dstM[i]);
  const lo = Math.min(...dstM), hi = Math.max(...dstM);
  const label = m => NAMES[((m % 12) + 12) % 12] + (Math.floor(m / 12) - 1);

  console.log("notes:", dstNotes.length, "| exact " + (shift > 0 ? "+" : "") + shift + " per note:", exact);
  console.log("range: " + label(lo) + "-" + label(hi) + "  (MIDI " + lo + "-" + hi + ")");

  if (chartPath) {
    const chart = JSON.parse(fs.readFileSync(chartPath, "utf8"));
    const IDS = chart.notes.map(n => n.id);
    const unknown = dstNotes.filter(t => !IDS.includes(t.id)).map(t => t.id + "(" + t.raw + ")");
    const inChart = lo >= midiOfChartLow(chart) && hi <= midiOfChartHigh(chart);
    console.log("chart " + chart.range.low + "-" + chart.range.high + " | unknown ids:", unknown.length ? unknown.join(",") : "none", "| fits:", inChart);
    if (unknown.length || !inChart) process.exitCode = 1;
  }
  if (!exact) process.exitCode = 1;

  if (dry) { console.log(dstBody); return; }
  if (!dstKey) { console.log("(no dstKey given: nothing written)"); return; }
  songs[dstKey] = Object.assign({}, src, {
    name: name || src.name,
    group: group || src.group,
    body: dstBody,
  });
  fs.writeFileSync("songs.json", JSON.stringify(songs, null, 2));
  console.log("wrote songs.json entry '" + dstKey + "'");
}
function midiOfChartLow(chart) { const m = /^([A-G])([#bs]?)(\d)$/.exec(chart.range.low); return chartMidi(m); }
function midiOfChartHigh(chart) { const m = /^([A-G])([#bs]?)(\d)$/.exec(chart.range.high); return chartMidi(m); }
function chartMidi(m) {
  const letter = m[1], acc = m[2] || "", oct = parseInt(m[3], 10);
  const conv = { s: "#", b: "b", "": "" }[acc];
  let pc = PC[letter];
  if (conv === "#") pc++; else if (conv === "b") pc--;
  if (pc < 0) { pc += 12; }
  return oct * 12 + 12 + pc;
}
main();
