#!/usr/bin/env python3
"""
mid2tab.py — Convert a Standard MIDI File into this ocarina tabber's notation.

Pure-stdlib (no deps). Parses SMF format 0/1, lists channels/instruments,
extracts one channel as a monophonic melody, quantizes onsets to a grid that
supports 16ths AND triplets, and emits `songs.json`-style body text with bar
lines and rests. Every bar is verified against the meter.

Usage:
  # 1) Inspect: see channels, GM instruments, ranges, first notes
  python3 mid2tab.py FILE.mid --inspect

  # 2) Extract a channel to tab (align to a starting measure, choose meter)
  python3 mid2tab.py FILE.mid --channel 2 --start-measure 13 --beats-per-bar 4

Key options:
  --channel N          MIDI channel (0-based) carrying the melody
  --start-measure M    1-based measure where the melody enters (its downbeat).
                       Notes before this are ignored; grid aligns here.
  --beats-per-bar B    Meter numerator in quarter-beats (4 = 4/4, 3 = 3/4,
                       2 = 2/4). Default 4.
  --bars N             Stop after N bars (default: until the melody's last note)
  --transpose S        Shift every note by S semitones (to fit A3-G6).
  --straight-16ths     Disable triplet detection (grid = 16ths only).

Notation emitted: NOTE/dur, r/dur (rest), -/dur (tie across bar),
durations /1 /2 /4 /8 /16, dotted `.`, triplet `t`. See the ocarina-melodies
skill / README for the full grammar.
"""
import sys, struct, argparse

GM = {40:'Violin',41:'Viola',42:'Cello',43:'Contrabass',44:'TremoloStrings',
      45:'PizzStrings',46:'OrchHarp',48:'StringEns1',49:'StringEns2',
      68:'Oboe',71:'Clarinet',72:'Piccolo',73:'Flute',74:'Recorder',
      75:'PanFlute',78:'Whistle',79:'Ocarina',56:'Trumpet',60:'FrenchHorn',
      0:'AcousticGrandPiano'}
NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']

def read_var(d, p):
    v = 0
    while True:
        b = d[p]; p += 1; v = (v << 7) | (b & 0x7f)
        if not b & 0x80:
            return v, p

def parse_midi(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'MThd', 'not a MIDI file'
    hlen = struct.unpack('>I', d[4:8])[0]
    fmt, ntrk, div = struct.unpack('>HHH', d[8:8+hlen])
    pos = 8 + hlen
    notes = []           # (start_tick, end_tick, channel, midi)
    progs = {}           # channel -> program number
    active = {}
    for _ in range(ntrk):
        assert d[pos:pos+4] == b'MTrk'
        tlen = struct.unpack('>I', d[pos+4:pos+8])[0]
        p = pos + 8; endp = p + tlen; t = 0; status = 0
        while p < endp:
            dt, p = read_var(d, p); t += dt
            b = d[p]
            if b & 0x80:
                status = b; p += 1
            if status == 0xFF:
                meta = d[p]; p += 1; ln, p = read_var(d, p); p += ln
                if meta == 0x2F:
                    break
            elif status in (0xF0, 0xF7):
                ln, p = read_var(d, p); p += ln
            else:
                ev = status & 0xF0; ch = status & 0x0F
                if ev == 0xC0:
                    progs.setdefault(ch, d[p]); p += 1
                elif ev == 0xD0:
                    p += 1
                elif ev in (0x80, 0x90, 0xA0, 0xB0, 0xE0):
                    d1 = d[p]; d2 = d[p+1]; p += 2
                    if ev == 0x90 and d2 > 0:
                        active[(ch, d1)] = t
                    elif ev == 0x80 or (ev == 0x90 and d2 == 0):
                        st = active.pop((ch, d1), None)
                        if st is not None:
                            notes.append((st, t, ch, d1))
        pos = endp
    notes.sort()
    return notes, progs, div

def nm(m):
    return NAMES[m % 12] + str(m // 12 - 1)

def inspect(notes, progs, div):
    print(f'ticks/quarter = {div}')
    chans = sorted({c for _, _, c, _ in notes})
    for ch in chans:
        ns = [n for n in notes if n[2] == ch]
        lo = min(n[3] for n in ns); hi = max(n[3] for n in ns)
        first = ns[0][0] / (div * 4)
        prog = progs.get(ch)
        inst = GM.get(prog, f'prog{prog}') if prog is not None else '?'
        head = ' '.join(nm(n[3]) for n in ns[:20])
        print(f'ch {ch:2d}  {inst:14s}  {len(ns):3d} notes  '
              f'enters bar {first:5.1f}  midi {lo}-{hi} ({nm(lo)}-{nm(hi)})')
        print(f'        first: {head}')

# duration table: units are 1/12 of a quarter (LCM of 16th=3 and 16th-triplet=2)
# quarter=12, half=24, whole=48, 8th=6, 16th=3
# dotted: /2.=36 /4.=18 /8.=9
# triplets (x2/3 of the plain value): /4t=8 /8t=4 /16t=2
U_PER_QUARTER = 12
DUR_TABLE = [  # (units, token)  -- longest first
    (48, '/1'), (36, '/2.'), (24, '/2'), (18, '/4.'), (12, '/4'),
    (9, '/8.'), (8, '/4t'), (6, '/8'), (4, '/8t'), (3, '/16'), (2, '/16t'),
]

def tokens_for(units, kind, name):
    """kind: 'note' | 'rest' | 'tie'. Greedy-decompose `units` into duration
    tokens. 'note' carries the pitch on the first piece and ties ('-') on the
    rest; 'tie' emits all pieces as ties; 'rest' emits rests. A small residue
    (humanized-MIDI rounding) is absorbed so bars always balance."""
    if units <= 0:
        return []
    # absorb a tiny residue by rounding to the nearest representable total
    if units % 2 == 1 and units not in (3, 9):   # 3=/16, 9=/8. are exact
        units += 1  # round odd sliver up to an even (triplet-grid) value
    out = []
    rem = units
    first = True
    for val, tk in DUR_TABLE:
        while rem >= val:
            if kind == 'rest':
                out.append('r' + tk)
            elif kind == 'tie':
                out.append('-' + tk)
            elif first:
                out.append(name + tk); first = False
            else:
                out.append('-' + tk)
            rem -= val
    if rem != 0:
        out.append(f'<UNQUANTIZED:{rem}>')
    return out

def convert(notes, div, channel, start_measure, beats_per_bar, bars_limit,
            transpose, straight, legato, min_note):
    zero = (start_measure - 1) * div * beats_per_bar
    u16 = div // 4            # ticks per 16th
    u48 = div // 12           # ticks per 1/12-quarter (triplet grid)
    def snap(tick):
        """Snap an onset to the 16th grid, UNLESS it is clearly a triplet
        position (closer to the 1/12 grid than the 16th grid). Returns the
        onset in 1/12-quarter units."""
        rel = tick - zero
        near16 = round(rel / u16) * u16
        near48 = round(rel / u48) * u48
        if straight or abs(rel - near16) <= abs(rel - near48):
            return round(near16 / u48)   # express 16th position in 1/12 units
        return round(near48 / u48)
    mono = []
    for st, en, ch, mi in notes:
        if ch != channel:
            continue
        if min_note is not None and mi < min_note:
            continue          # drop chord notes below the melody register
        s = snap(st); e = snap(en)
        if e <= s or e <= 0:
            continue
        s = max(0, s)
        mono.append([s, e, mi + transpose])
    mono.sort()
    # resolve overlaps: truncate a note at the next onset (monophonic)
    for i in range(len(mono) - 1):
        if mono[i][1] > mono[i+1][0]:
            mono[i][1] = mono[i+1][0]
    mono = [m for m in mono if m[1] > m[0]]
    # Build events. Two rhythm styles:
    #   legato: each note lasts until the next onset (no rests) — cleanest grid.
    #   articulated (default): keep the real note length, fill the gap to the
    #     next onset with a rest (captures the detached, breathy phrasing).
    events = []
    for i, (s, e, mi) in enumerate(mono):
        nxt = mono[i+1][0] if i+1 < len(mono) else e
        if legato:
            events.append((s, nxt - s, nm(mi)))
        else:
            events.append((s, e - s, nm(mi)))
            if nxt > e:
                events.append((e, nxt - e, None))
    bar_units = beats_per_bar * U_PER_QUARTER  # 1/12-quarter units per bar
    # emit, splitting notes/rests at bar edges
    toks = []
    for pos, dur, name in events:
        end = pos + dur; a = pos
        edges = [x for x in range(bar_units, end, bar_units) if pos < x < end]
        first_seg = True
        for c in edges + [end]:
            seg = c - a
            if name is None:
                toks.extend(tokens_for(seg, 'rest', name))
            elif first_seg:
                toks.extend(tokens_for(seg, 'note', name))
            else:
                # note continues past a bar edge: emit as ties
                toks.extend(tokens_for(seg, 'tie', name))
            first_seg = False
            a = c
    # insert bar lines
    def units_of(tk):
        if '/' not in tk:
            return 0
        base = tk.split('/', 1)[1]
        dotted = '.' in base
        triplet = base.endswith('t')
        num = int(''.join(ch for ch in base if ch.isdigit()))
        u = (48 // num)
        if dotted: u = int(u * 1.5)
        if triplet: u = u * 2 // 3
        return u
    res = []; cur = 0; ne = bar_units; nb = 1
    for tk in toks:
        while cur >= ne - 1e-9:
            res.append('|'); ne += bar_units; nb += 1
            if bars_limit and nb > bars_limit:
                break
        if bars_limit and nb > bars_limit:
            break
        res.append(tk); cur += units_of(tk)
    body = ' '.join(res)
    # verify each bar
    ok = True
    for i, b in enumerate(body.split('|')):
        if not b.strip():
            continue
        tot = sum(units_of(t) for t in b.split())
        tag = '' if tot == bar_units else f'  <<< {tot}/{bar_units} MISMATCH'
        if tag:
            ok = False
        print(f'bar {i+1}: {tot}/{bar_units}{tag}  {b.strip()}', file=sys.stderr)
    print(f'\nall bars OK: {ok}\n', file=sys.stderr)
    return body

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('midi')
    ap.add_argument('--inspect', action='store_true')
    ap.add_argument('--channel', type=int)
    ap.add_argument('--start-measure', type=int, default=1)
    ap.add_argument('--beats-per-bar', type=int, default=4)
    ap.add_argument('--bars', type=int, default=0)
    ap.add_argument('--transpose', type=int, default=0)
    ap.add_argument('--straight-16ths', action='store_true')
    ap.add_argument('--legato', action='store_true',
                    help='each note lasts until the next onset (no rests)')
    ap.add_argument('--min-note', type=int, default=None,
                    help='drop notes below this MIDI number (keep the top '
                         'melody voice of a chordal/ensemble channel)')
    a = ap.parse_args()
    notes, progs, div = parse_midi(a.midi)
    if a.inspect or a.channel is None:
        inspect(notes, progs, div)
        if a.channel is None:
            print('\nPick a --channel and re-run with --start-measure.')
        return
    body = convert(notes, div, a.channel, a.start_measure, a.beats_per_bar,
                   a.bars, a.transpose, a.straight_16ths, a.legato, a.min_note)
    print(body)

if __name__ == '__main__':
    main()
