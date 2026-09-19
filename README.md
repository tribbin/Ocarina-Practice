# Ocarina Tab Maker

A browser-based tab maker and practice companion for the ocarina. Type notes, get hole-fingering tabs on the ocarina's template, hear the song played back through a synthesized ocarina, and practice hands-on with microphone feedback.

Built with plain HTML/CSS/JavaScript — no build step, no dependencies.

## Features

- **Tab sheets** — fingerings rendered on the ocarina template as you type; display as a grid, scrolling line, or one note at a time. Printable and downloadable.
- **Immediate playback** — a synthesized ocarina voice plays your melody with tempo and swing dials; click any note to start from there.
- **Practice mode** — the song only advances when you hit each note in tune through the microphone, guided by a built-in tuner. Ties hold continuously; `~` slides become chains you must travel through pitch by pitch; rests count on the clock.
- **Zen mode** — distraction-free fullscreen practice with shareable links that open straight to a given song and ocarina.
- **Piano keyboard** — audition notes by ear, right-click to add them to the melody.
- **Library** — ready-made songs and scales, save/load files, and a personal library in-browser.
- **Multiple instruments** — Triple Bass C, Double Alto C, and the 12-hole Alto C, each with its own fingerings and template.

## Notation

| | |
|---|---|
| Notes | `C4` `D4` … `C#4`/`Db4` |
| Bars / rests | `\|` / `r` |
| Ties / slides | `-` / `~` (e.g. `F4 ~ A4`) |
| Staccato | `!` (e.g. `C4!`) |
| Durations | `/1` whole · `/2` half · `/4` quarter · `/8` `/16` · `.` dotted (e.g. `/2.`) |
| Triplets | `t` (e.g. `A4/8t B4/8t C5/8t`) |
| Title / tempo | `# Song title` · `# tempo 96` (header, or inline to change mid-song) |

## Running it

Serve the folder over **localhost** (the microphone in practice mode requires HTTPS or localhost), e.g.:

```
python -m http.server 8000
```

then open `http://localhost:8000`. Deploying as a static site (e.g. GitHub Pages) works as-is.

Extending it: songs live in `songs.json`, and each instrument's fingerings and template in `fingerings*.json` / `ocarina-template*.svg` — new instruments and songs can be added without touching code.
