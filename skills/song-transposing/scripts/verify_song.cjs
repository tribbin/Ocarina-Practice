// Verify a songs.json entry against js/parse.js and (optionally) a fingering chart.
// Usage (repo root): node skills/song-transposing/scripts/verify_song.cjs <songKey> [chart.json]
//
// Checks: parseable, per-note IDs resolvable on the chart, MIDI range inside the
// chart range, no stray tokens (a note-count far from expectation usually means a
// broken label bracket feeding letters to the parser). The parser's own syntax
// gate runs here too: any "bad" chip (junk the grammar cannot consume) fails the
// entry — a shipped or transposed body must parse clean by construction.
// Names avoid parse.js globals (it already defines midiOf, NOTES, etc.).
// Supports (inline/bar brackets) are not melody: they stay out of the note list
// and the chart/range math.
const fs = require("fs");
const NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const PC = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
const tokMidi = t => {
  const m = /^([A-G])(s|b)?(\d+)$/.exec(t.id);
  if (!m) return null;
  let pc = PC[m[1]];
  if (m[2] === "s") pc++; else if (m[2] === "b") pc--;
  return (parseInt(m[3], 10) + 1) * 12 + pc;
};
const chartMidi = s => {
  const m = /^([A-G])([#bs]?)(\d)$/.exec(s);
  const conv = (m[2] || "").replace("s", "#");
  let pc = PC[m[1]] + (conv === "#" ? 1 : conv === "b" ? -1 : 0);
  if (pc < 0) pc += 12;
  return parseInt(m[3], 10) * 12 + 12 + pc;
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

const [key, chartPath] = process.argv.slice(2);
const songs = JSON.parse(fs.readFileSync("songs.json", "utf8"));
if (!songs[key]) { console.error("no song '" + key + "'"); process.exit(2); }
const parse = loadParse();
const toks = parse(songs[key].body);
const notes = toks.filter(t => t.type === "note");
const bad = toks.filter(t => t.type === "bad");
const mids = notes.map(tokMidi);
const lo = Math.min(...mids), hi = Math.max(...mids);
const label = m => NAMES[((m % 12) + 12) % 12] + (Math.floor(m / 12) - 1);
let badCode = 0;
console.log(key, "->", notes.length, "notes (total tokens " + toks.length +
            ", bad chips " + bad.length + (bad.length ? ": " + bad.map(t => JSON.stringify(t.raw)).join(" ") : "") +
            ") | range " + label(lo) + "-" + label(hi) + " (MIDI " + lo + "-" + hi + ")");
if (bad.length) badCode = 1;
if (chartPath) {
  const chart = JSON.parse(fs.readFileSync(chartPath, "utf8"));
  const IDS = chart.notes.map(n => n.id);
  const unknown = notes.filter(t => !IDS.includes(t.id)).map(t => t.id + "(" + t.raw + ")");
  const flo = chartMidi(chart.range.low), fhi = chartMidi(chart.range.high);
  const fits = lo >= flo && hi <= fhi;
  console.log("chart " + chart.range.low + "-" + chart.range.high + " | unknown ids:", unknown.length ? unknown.join(",") : "none", "| fits chart:", fits);
  if (unknown.length || !fits) badCode = 1;
}
process.exit(badCode);
