#!/usr/bin/env python3
# parse.js edge-case acceptance: the front door of every feature. Melody
# grammar (notes/accidentals/inheritance, durations/dots/triplets, staccato in
# both spellings, ties/slides/rests, bars & sections, inline tempo), the
# header helpers (withPlayHeaders/withTempoLine/withTitleAndTempo,
# titleFromText/swingFromText), and the pitch helpers (pretty/midiOf/
# spelledLabel/octSub). Support-bracket grammar has its own suite
# (testsupport_accepts_brackets.py).
#
#   python3 tests/parse_edges.py      # headless & silent

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
HEADLESS = "--headed" not in sys.argv
WAIT = ("typeof parse === 'function'"
        " && typeof withPlayHeaders === 'function'"
        " && typeof midiOf === 'function'")


from suite_server import start_server


NOTES = r"""
() => {
  const t = (src) => parse(src);
  const n0 = (src) => { const ts = t(src); return ts[0] || null; };
  return {
    // shape of the default note
    plain: n0("C4"),
    // lowercase input, display spelling preserved
    lower: n0("c4"),
    // accidentals: sharp targets enharmonic id always written sharps-first
    sharpSpell: n0("C#4"),
    // s-form IS melody grammar now (decision a): Cs4 == C#4, display
    // spelling normalized to the hash form
    shorthand: t("Cs4 C5"),
    // flats re-spell into substance ids (Db4 -> Cs4), octave-adjacent flats
    // shift octave: Cb4 -> B3
    flat: n0("Db4"),
    flatC: n0("Cb4"),
    flatA: n0("Ab4"),
    // octave inheritance: note without octave continues the last one
    inherit: t("C4 D"),
    inheritAcc: t("Db4 E"),
    // durations
    half: n0("C4/2"),
    dottedHalf: n0("C4/2."),
    triplet: n0("C4/4t"),
    whole: n0("C4/1"),
    // staccato, both legal spellings (normalized before matching)
    stacAfter: n0("C4!"),
    stacBefore: n0("C4!/8"),
    stacAfterDur: n0("C4/8!"),
    // junk around legal tokens surfaces as visible "bad" chips (decision b):
    // garbage, typos, multi-digit octaves — everything unparsable becomes a
    // chip instead of silently vanishing into a wrong pitch or nothing
    junkLetter: t("H4 C4"),
    c10: t("C10"),
    c44: t("C44"),
    badMiddle: t("C4 foo D4"),
    badTail: t("C4 zz"),
    // ties: continuation keeps id + original spelling (the duration attaches
    // without a space: "-/2"; spaced "- /2" surfaces the "/2" as a bad chip)
    tie: t("C4 -/2").map(x => ({type: x.type, id: x.id,
                                 sl: x.spellLetter, so: x.spellOct})),
    // orphan tie (no note before it) is junk now: rests are written with `r`
    // (decision: only r means rest; a bare dash is a typo, show it)
    leadTie: t("-/2"),
    // dash chained after a BAR keeps the previous note's tie (book of songs
    // works this way: "A4/2. | -/2.")
    tieAcrossBar: t("A4/2 | -/2"),
    // slides picture from the previous note; rests break a pending slide
    slide: t("C4 ~ D4"),
    slideBroken: t("C4 ~ r D4"),
    // rests over their own lengths
    rest: n0("r/2."),
    // bars and section names
    bar: t("C4 | [Chorus] | D4"),
    // hidden support marker between pitches
    bassBetween: t("C4 [C2] D4").map(x => x.type),
    // inline tempo change emits a token; leading header does not
    headerTempo: t("# tempo 96\nC4 D4"),
    inlineTempo: t("# tempo 96\nC4 # tempo 130 D4"),
  };
}
"""

HELPERS = r"""
() => {
  const near = (a, b) => Math.abs(a - b) < 1e-6;
  return {
    prettySharp: pretty("Cs4"),
    prettyPlain: pretty("C4"),
    midiC4: midiOf("C4"), midiCs4: midiOf("Cs4"), midiB3: midiOf("B3"),
    midiNeg: midiOf("C-1"),
    midiNull: [midiOf(""), midiOf("H4"), midiOf("Cs")],
    octSub4: octSub(44),
    spelledFlat: spelledLabel({type: "note", id: "Cs4", spellLetter: "D",
                               spellAcc: "b", spellOct: 4}),
    spelledInherit: spelledLabel({type: "note", id: "C4"}),
    labelRest: spelledLabel({type: "rest"}),
    rangeUnknown: isOutOfRange("C9") === (rangeCheck("C9") === "below" || rangeCheck("C9") === "above"),
  };
}
"""

HEADERS = r"""
() => {
  return {
    rT: [tempoFromText("# hi\n# tempo 96\nC4"), tempoFromText("# hi\nC4")],
    rS: [swingFromText("# tempo 70\n# swing 55\nC4"), swingFromText("# tempo 70\nC4")],
    rTitle: [titleFromText("# Saria's Song\n# tempo 96\nC4"),
             titleFromText("# tempo 96\nC4"), titleFromText("")],
    w: withPlayHeaders("C4 D4", "My Song", 96, 0),
    wPreserveInline: withPlayHeaders("C4 # tempo 130\nD4", "T", 96, 0),
    wReplacesOld: withPlayHeaders("# old\n# tempo 90\nC4", "N", 96, 10),
    wKeepsOtherHeader: withPlayHeaders("# My Title\n# tempo 90\nC4", null, 96, 0),
    wNoNameNoHeader: withPlayHeaders("C4 D4", null, 96, 0),
    wt: withTempoLine("# swing 40\nC4", 80),
    wtt: withTitleAndTempo("C4", "Fresh", 120),
  };
}
"""


def main():
    failures = []
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS)
            page = browser.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(base)
            page.wait_for_function(WAIT)
            n = page.evaluate(NOTES)
            h = page.evaluate(HELPERS)
            w = page.evaluate(HEADERS)

            def check(key, cond, msg):
                if not cond:
                    failures.append(f"{key}: {msg}")

            # --- note shape ---
            pl = n["plain"]
            check("plain", pl and pl["type"] == "note" and pl["id"] == "C4"
                  and pl["dur"] == 4 and not pl["dotted"] and not pl["triplet"]
                  and pl["beats"] == 1,
                  f"basic C4 shape wrong: {pl!r}")
            check("plain", pl["spellLetter"] == "C" and pl["spellAcc"] == ""
                  and pl["spellOct"] == 4, f"C4 spelling fields: {pl!r}")
            check("lower", n["lower"]["id"] == "C4"
                  and n["lower"]["spellLetter"] == "C", "lowercase must normalize")
            check("shorthand", len(n["shorthand"]) == 2
                  and n["shorthand"][0]["id"] == "Cs4"
                  and n["shorthand"][0]["spellAcc"] == "#"
                  and n["shorthand"][1]["id"] == "C5",
                  f"s-form must parse like a sharp with hash display: {n['shorthand']!r}")
            check("sharpSpell", n["sharpSpell"]["id"] == "Cs4"
                  and n["sharpSpell"]["spellAcc"] == "#",
                  "C#4 -> Cs4 with # recorded for display")
            check("flat", n["flat"]["id"] == "Cs4"
                  and n["flat"]["spellLetter"] == "D"
                  and n["flat"]["spellAcc"] == "b" and n["flat"]["spellOct"] == 4,
                  f"Db4 must stay spelled D-flat with id Cs4: {n['flat']!r}")
            check("flatC", n["flatC"]["id"] == "B3"
                  and n["flatC"]["spellOct"] == 4,
                  f"Cb4 must enspell to B3 (octave drop) : {n['flatC']!r}")
            check("flatA", n["flatA"]["id"] == "Gs4", "Ab4 -> Gs4")
            inherit = n["inherit"]
            check("inherit", len(inherit) == 2 and inherit[0]["id"] == "C4"
                  and inherit[1]["id"] == "D4",
                  f"octave inheritance C4 D -> D4: {inherit!r}")
            inha = n["inheritAcc"]
            check("inheritAcc", len(inha) == 2 and inha[1]["id"] == "E4"
                  and inha[1]["spellOct"] == 4,
                  f"Db4 E: octave inherits, accidental does not: {inha!r}")
            # --- durations (4/dur * dotted 1.5 * triplet 2/3) ---
            check("half", n["half"]["beats"] == 2 and n["half"]["dur"] == 2,
                  "quarter default-> /2 must be 2 beats")
            dh = n["dottedHalf"]
            check("dottedHalf", dh["beats"] == 3 and dh["dotted"], "/2. = 3 beats")
            tr = n["triplet"]
            check("triplet", tr["triplet"] and abs(tr["beats"] - 2 / 3) < 1e-6,
                  "/4t = 2/3 beat")
            check("whole", n["whole"]["beats"] == 4, "/1 = 4 beats")
            check("stacAfter", n["stacAfter"]["staccato"] is True,
                  "C4! must flag staccato")
            check("stacBefore", n["stacBefore"]["staccato"] is True
                  and n["stacBefore"]["dur"] == 8,
                  "C4!/8 normalizes to dur-then-bang (see parse.js:8)")
            check("stacAfterDur", n["stacAfterDur"]["staccato"] is True
                  and n["stacAfterDur"]["dur"] == 8, "C4/8! parses staccato")
            # --- junk handling: everything unparsable becomes a bad chip ---
            jl = n["junkLetter"]
            check("junkLetter", len(jl) == 2 and jl[0]["type"] == "bad"
                  and jl[0]["raw"] == "H4" and jl[1]["id"] == "C4",
                  f"junk must surface as a visible bad chip: {jl!r}")
            c10 = n["c10"]
            check("c10", len(c10) == 1 and c10[0]["type"] == "bad"
                  and c10[0]["raw"] == "C10",
                  f"C10 must be a visible bad chip, never a wrong pitch "
                  f"(pre-fix produced C1): {c10!r}")
            c44 = n["c44"]
            check("c44", len(c44) == 1 and c44[0]["type"] == "bad"
                  and c44[0]["raw"] == "C44",
                  f"C44 must be a visible bad chip: {c44!r}")
            bm = n["badMiddle"]
            check("badMiddle", len(bm) == 4 and bm[1]["id"] == "F4"
                  and bm[2]["type"] == "bad" and bm[2]["raw"] == "oo"
                  and bm[3]["id"] == "D4",
                  f"stray LETTERS are legal octaveless notes by design (f -> "
                  f"F4); the remaining junk becomes a bad chip: {bm!r}")
            bt = n["badTail"]
            check("badTail", len(bt) == 2 and bt[1]["type"] == "bad"
                  and bt[1]["raw"] == "zz",
                  f"trailing junk must surface too: {bt!r}")
            # --- ties & slides ---
            tie = n["tie"]
            check("tie", len(tie) == 2 and tie[1]["type"] == "tie"
                  and tie[1]["id"] == "C4" and tie[1]["sl"] == "C"
                  and tie[1]["so"] == 4,
                  f"tie continuation must carry id + original spelling: {tie!r}")
            lt = n["leadTie"]
            check("leadTie", len(lt) == 1 and lt[0]["type"] == "bad"
                  and lt[0]["raw"] == "-/2",
                  f"orphan tie must surface as a bad chip, not act as a "
                  f"rest: {lt!r}")
            tb = n["tieAcrossBar"]
            check("tieAcrossBar", len(tb) == 3 and tb[2]["type"] == "tie"
                  and tb[2]["id"] == "A4",
                  f"dashes after bars keep tying the previous note: {tb!r}")
            sl = n["slide"]
            check("slide", isinstance(sl, list) and len(sl) == 2
                  and sl[1]["slide"] is True and sl[1]["slideFrom"] == "C4",
                  "D4 after ~ must slide from C4")
            sb = n["slideBroken"]
            check("slideBroken", len(sb) == 3 and "slide" not in sb[2],
                  "a rest must break a pending slide (tokens: note, rest, note)")
            rs = n["rest"]
            check("rest", rs["type"] == "rest" and rs["dotted"]
                  and rs["beats"] == 3, "r/2. = dotted rest 3 beats")
            bar = n["bar"]
            check("bar", len(bar) == 4 and bar[1]["type"] == "bar"
                  and bar[1].get("desc") == "Chorus",
                  f"section bar keeps desc: {bar!r}")
            bb = n["bassBetween"]
            check("bassBetween", bb == ["note", "bass", "note"],
                  f"inline support marker tokenizes to a hidden bass token: {bb!r}")
            ht = n["headerTempo"]
            check("headerTempo", len(ht) == 2,
                  "leading '# tempo' header must not emit a tempo token")
            it = n["inlineTempo"]
            check("inlineTempo", len(it) == 3 and it[1]["type"] == "tempo"
                  and it[1]["bpm"] == 130 and it[2]["id"] == "D4",
                  f"mid-song '# tempo' must emit the change token: {it!r}")

            # --- helpers ---
            check("prettySharp", h["prettySharp"] == "C#4", "pretty Cs4")
            check("prettyPlain", h["prettyPlain"] == "C4", "pretty C4 id")
            check("midiC4", h["midiC4"] == 60, "C4 = midi 60")
            check("midiCs4", h["midiCs4"] == 61, "Cs4 = midi 61")
            check("midiB3", h["midiB3"] == 59, "B3 = midi 59")
            check("midiNeg", h["midiNeg"] == 0, "C-1 = midi 0")
            check("midiNull", h["midiNull"] == [None, None, None],
                  "midiOf must reject junk")
            check("octSub4", h["octSub4"] == "₄₄", "octave subtitle digits")
            check("spelledFlat", h["spelledFlat"] == "D♭₄",
                  f"flat display uses unicode octaves: {h['spelledFlat']!r}")
            check("spelledInherit", h["spelledInherit"] == "C₄",
                  f"colored octave rendering: {h['spelledInherit']!r}")
            check("labelRest", h["labelRest"] == "",
                  "spelledLabel must be empty for non-notes")
            check("rangeUnknown", h["rangeUnknown"] is True,
                  "isOutOfRange must agree with its rangeCheck primitive")

            # --- headers ---
            check("tempoFromText", w["rT"] == [96, None], f"{w['rT']!r}")
            check("swingFromText", w["rS"] == [55, None], f"{w['rS']!r}")
            check("titleFromText", w["rTitle"] == ["Saria's Song", "", ""],
                  f"{w['rTitle']!r}")
            wn = w["w"]
            check("wHeader", wn == "# My Song\n# tempo 96\nC4 D4", f"{wn!r}")
            wp = w["wPreserveInline"]
            check("wPreserveInline", "# tempo 130" in wp.split("\n", 2)[2]
                  and wp.startswith("# T\n# tempo 96"),
                  f"inline tempo must survive withPlayHeaders: {wp!r}")
            wr = w["wReplacesOld"]
            check("wReplacesOld", wr == "# N\n# tempo 96\n# swing 10\nC4",
                  f"old leading headers replaced exactly: {wr!r}")
            wk = w["wKeepsOtherHeader"]
            check("wKeepsOtherHeader", wk == "# My Title\n# tempo 96\nC4",
                  f"non-tempo header line preserved, tempo replaced: {wk!r}")
            wnn = w["wNoNameNoHeader"]
            check("wNoNameNoHeader", wnn == "# tempo 96\nC4 D4",
                  f"no title when body had none: {wnn!r}")
            wt = w["wt"]
            check("wt", wt == "# tempo 80\n# swing 40\nC4",
                  f"withTempoLine keeps swing: {wt!r}")
            wtt = w["wtt"]
            check("wtt", wtt == "# Fresh\n# tempo 120\nC4",
                  f"withTitleAndTempo default swing: {wtt!r}")

            if errs:
                failures.append(f"page errors {errs}")
            browser.close()
    finally:
        httpd.shutdown()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: melody grammar, enharmonic spelling, junk handling, ties/"
          "slides/rest, section bars, inline tempo and the header helpers all "
          "match spec.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
