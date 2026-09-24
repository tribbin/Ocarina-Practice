// Shared music-theory math — the single source for note-id pitch mapping
// (§5 M1 dedup: audio.js, ui.js and practice.js each kept a private copy
// until now). THE EXCEPTION is js/parse.js, whose midiOf stays local on
// purpose: the song-transposing skill loads parse.js raw through a
// window-shim eval that strips export blocks but cannot carry imports.
//
// midiOf accepts NEGATIVE octaves (the superset grammar, matching
// parse.js's range labels) and returns null for anything unparsable —
// callers apply their own fallbacks (audio 440 Hz, ui 69 = A4).

export const SEMITONES = { C: 0, Cs: 1, D: 2, Ds: 3, E: 4, F: 5, Fs: 6,
                           G: 7, Gs: 8, A: 9, As: 10, B: 11 };

export function midiOf(id) {
  const m = String(id || "").match(/^([A-G]s?)(-?\d)$/);
  if (!m || !(m[1] in SEMITONES)) return null;
  return SEMITONES[m[1]] + (+m[2] + 1) * 12;
}

export function freqOf(id) {
  const midi = midiOf(id);
  if (midi == null) return 440;
  return 440 * Math.pow(2, (midi - 69) / 12);
}
