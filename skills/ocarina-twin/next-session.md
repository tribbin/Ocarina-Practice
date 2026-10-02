# Next session: noise shape and note start

Measured 2026-10-02 from the ladder holds. The sine body is close enough to leave alone. Do not retune attack, release, or the `~` join except for the rise times below. Do not bring back the band-pass fitter.

Levels are residual energy after notching H1–H6, relative to the fundamental peak. The halo column still contains skirt leakage, so treat it as an upper bound. Rise is the 10–90% energy time at the onset.

## What the shipped voice does wrong

The fitter opens one air band around the loudest residual peak and clamps its bottom at 800 Hz. On the high 12-hole notes that peak is the note's own skirt, so the voice plays a resonant band under the note. That is the shell.

Shipped 12-hole rows:

| note | f0 | shipped air | shipped air dB | measured air peak | measured 2–4 kHz |
|---|---|---|---|---|---|
| C5 | 524 | 2280–3780 | −50 | 1050 | −85 |
| G5 | 784 | 800–1964 | −42 | 1569 | −73 |
| D6 | 1173 | 800–2168 | −45 | 2346 | −66 |
| E6 | 1319 | 875–2375 | −42 | 2632 | −65 |
| F6 | 1397 | 878–2378 | −42 | 2782 | −64 |

F6's air starts 500 Hz below the note and is about 20 dB louder than the measured 2–4 kHz residual. The real peak is at 2782 Hz, above the note. C5 is the other way round: the shipped band is a high hiss the take does not have.

The floor is a residual median shifted by a fixed +28 dB and clamped to −62..−46. A quiet bass hold and a loud alto hold land in the same range. The attack is 8 ms of silence and a 28 ms rise on every row, including A3.

## Noise, by chamber

Bass whoosh is under about 2 kHz and falls as the note rises. Hiss above 5 kHz is absent on the low chamber (about −105 dB) and only reaches the mid −80s on the high chamber.

Oak chamber 1:

| note | f0 | rise ms | H2 | H3 | H4 | whoosh | 2–4 kHz | 5–11 kHz | air peak |
|---|---|---|---|---|---|---|---|---|---|
| C4 | 258 | 69 | −27 | −26 | −45 | −45 | −70 | −103 | 1036 |
| D4 | 293 | 22 | −32 | −28 | −46 | −47 | −65 | −104 | 2639 |
| E4 | 328 | 27 | −39 | −37 | −58 | −54 | −72 | −109 | 986 |
| F4 | 351 | 26 | −31 | −42 | −48 | −55 | −79 | −109 | 1055 |
| G4 | 396 | 31 | −46 | −49 | −52 | −65 | −81 | −109 | 1186 |
| A4 | 440 | 35 | −48 | −55 | −60 | −76 | −87 | −108 | 2662 |
| B4 | 493 | 54 | −45 | −45 | −58 | −69 | −82 | −107 | 1483 |
| C5 | 522 | 31 | −52 | −44 | −61 | −68 | −83 | −110 | 1567 |
| D5 | 587 | 45 | −54 | −63 | −62 | −69 | −71 | −103 | 1762 |

Oak chamber 2 is the honk region. E5 and F5 really do have H2, H3 and H4 within a few dB. Keep H3 under H2. The air peak is 1.5–2.6 kHz, not a band under the note. Hiss is still about −96 dB.

| note | f0 | rise ms | H2 | H3 | H4 | whoosh | 2–4 kHz | 5–11 kHz | air peak |
|---|---|---|---|---|---|---|---|---|---|
| E5 | 655 | 21 | −37 | −36 | −36 | −63 | −65 | −104 | 2620 |
| F5 | 697 | 37 | −35 | −33 | −48 | −57 | −60 | −96 | 2093 |
| G5 | 779 | 45 | −41 | −43 | −58 | −61 | −67 | −97 | 1557 |
| B5 | 983 | 13 | −34 | −56 | −57 | −59 | −73 | −96 | 1964 |
| C6 | 1044 | 26 | −40 | −79 | −72 | −63 | −68 | −99 | 2088 |

Oak chamber 3 whoosh is gone (about −80 dB). What remains is a mid band around the air peak, 2.3–3.3 kHz, and a hiss that has come up to −78..−89 dB.

12-hole. Low notes are a thin whoosh and almost no hiss. From D6 up the hiss rises (F6 −80 dB) and the air peak stays above the note (D6 2346, E6 2632, F6 2782). Do not open a band below f0.

| note | f0 | rise ms | H2 | H3 | H4 | whoosh | 2–4 kHz | 5–11 kHz | air peak |
|---|---|---|---|---|---|---|---|---|---|
| C5 | 525 | 13 | −44 | −48 | −70 | −65 | −85 | −108 | 1050 |
| D5 | 591 | 18 | −50 | −47 | −69 | −71 | −83 | −102 | 1771 |
| E5 | 654 | 15 | −52 | −48 | −74 | −66 | −80 | −103 | 1309 |
| F5 | 694 | 15 | −42 | −39 | −56 | −65 | −66 | −98 | 2087 |
| G5 | 785 | 15 | −39 | −50 | −58 | −63 | −73 | −96 | 1569 |
| A5 | 882 | 23 | −43 | −64 | −66 | −67 | −78 | −96 | 1762 |
| B5 | 984 | 38 | −48 | −61 | −71 | −65 | −75 | −91 | 1978 |
| C6 | 1040 | 15 | −50 | −52 | −80 | −69 | −69 | −92 | 3122 |
| D6 | 1172 | 52 | −46 | −51 | −66 | −72 | −66 | −86 | 2346 |
| E6 | 1319 | 59 | −47 | −48 | −75 | −69 | −65 | −83 | 2632 |
| F6 | 1389 | 16 | −35 | −53 | −54 | −67 | −64 | −80 | 2782 |

Double alto, chamber split at E6. Chamber 1 hiss is −100 dB or quieter. Chamber 2 hiss rises to about −70 dB and the air peak moves to 3.5–4.7 kHz. C7's −38 dB mid band is one hold, not a target.

## Start-up

The bass low end is the slow one. C4 is 69 ms, B4 54 ms, D5 45 ms. The 12-hole low notes are 13–18 ms, except B5 (38), D6 (52) and E6 (59). Double alto G5 (120) and C6 (106) are soft entries, not a chamber law. A rise under about 20 ms is the current voice. A rise over 40 ms is not.

Fit `atk_speak_s` from these rises, per hold, and interpolate inside the chamber. Leave `rel_s` and the `~` hold (`dur + rel`) alone. Chiff stays off notes shorter than a blow. A bass start gets a longer, quieter chiff. An alto start does not get a louder one to compensate.

## How to fit the noise

Three pieces, not one band:

- Halo: narrow, on f0. Do not trust the halo column above as a level.
- Whoosh: only where the table shows it. Oak chamber 1 under 2 kHz. Gone by oak chamber 3. 12-hole low notes around −65 dB, not a shell.
- Hiss: 5–11 kHz. About −105 dB on the bass low chamber, −80 dB on 12-hole F6, −70 dB on the double's second chamber. Never the alto 2.8/4 kHz split on a bass.

The air band must start above f0. On D6–F6 of the 12-hole, center it on the measured air peak and keep it narrower than the shipped 1.5 kHz. Drop the −46 dB floor clamp on those notes.

## Done on voice-noise-rise

Shipped as v3l-chamber. Air bands start above f0; 12-hole D6–F6 are centered on the measured peak (about 700 Hz wide) and no longer clamped up to −46. Whoosh, hiss and a narrow halo are separate rows. `atk_speak_s` follows the measured rises (bass C4 is 69 ms). `rel_s` and the `~` hold are unchanged. Bass chiff is longer and quieter; alto chiff is not boosted.

The slope floor is held 8 dB under the whoosh so it cannot fill the gap the three pieces leave. Partials, `rel_s`, and the `~` hold are still untouched.
Playback uses the same +28 dB residual-to-RMS shift as v3k, without the −46 clamp and without opening the band under f0. Raw residual dB as a gain was why the air disappeared.

The v3k air band, floor and slope are restored from main. The residual rewrite had replaced that tuned air. Rises stay fitted. Extra whoosh and hiss rows are not shipped.
