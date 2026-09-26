"""Dump a MuseScore .mscz score's written music staff by staff.

Usage: python3 mscx_dump.py FILE.mscz [staffNumber ...] [--measures 11,12-14]

Prints every measure as written tokens: P<pitches>_<type>dots (+8/+16 tie
flags), R_<type>dots for rests, and `gP...` for grace notes (no grid time).
This is the readable ground truth for MIDI-to-tab conversions when a score
exists: written durations outrank the MIDI performance, whose releases are
early. Traps the dump exposes deliberately: pitch and dots live on <Note>
under <Chord> (not on the Chord), measure irregularities print as `L=5/4`,
and grace runs print as 32nds.

Stdlib only. Pair with mid2tab.py --inspect: convert from onsets, read
rhythm truth here, tally every bar to its time signature before shipping.
"""
import sys, zipfile, xml.etree.ElementTree as ET

NM = {0: 'C', 1: 'Cs', 2: 'D', 3: 'Ds', 4: 'E', 5: 'F', 6: 'Fs',
      7: 'G', 8: 'Gs', 9: 'A', 10: 'As', 11: 'B'}


def parse_range(spec):
    out = set()
    for part in spec.split(','):
        if '-' in part:
            a, b = part.split('-')
            out.update(range(int(a), int(b) + 1))
        elif part:
            out.add(int(part))
    return out


def main():
    path = sys.argv[1]
    want_staff = {int(a) for a in sys.argv[2:] if a.isdigit()}
    want_meas = None
    if '--measures' in sys.argv:
        want_meas = parse_range(sys.argv[sys.argv.index('--measures') + 1])
    z = zipfile.ZipFile(path)
    mscx_name = next((n for n in z.namelist() if n.endswith('.mscx')), None)
    if not mscx_name:
        sys.exit('no .mscx inside ' + path)
    root = ET.fromstring(z.read(mscx_name))
    score = root.find('Score')
    parts = {}
    for p in score.findall('Part'):
        st = p.find('Staff')
        inst = p.find('Instrument')
        tn = inst.findtext('trackName') if inst is not None else '?'
        parts[st.get('id')] = (tn or '?').split(',')[0]

    for i, sb in enumerate(score.findall('Staff')):
        sid = i + 1
        msrs = sb.findall('Measure')
        if want_staff and sid not in want_staff:
            continue
        print(f'== staff {sid} = {parts.get(sb.get("id"), sb.get("id"))}: '
              f'{len(msrs)} measures')
        for j, mm in enumerate(msrs):
            mn = mm.get('len', '')
            if want_meas and (j + 1) not in want_meas:
                continue
            out = []
            for c in mm.iter():
                if c.tag == 'Chord':
                    ns = c.findall('Note')
                    grace = any(n.find('grace') is not None for n in ns) \
                        or c.find('grace') is not None
                    dt = c.findtext('durationType') or 'quarter'
                    dots = len(c.findall('dot')) + \
                        sum(len(n.findall('dot')) for n in ns)
                    ties = ''.join(
                        ('+' if n.find('tie') is not None else '')
                        for n in ns)
                    pits = '/'.join(
                        NM[int(n.findtext('pitch')) % 12]
                        + str(int(n.findtext('pitch')) // 12 - 1)
                        for n in ns if n.findtext('pitch') is not None) or '?'
                    out.append(('g' if grace else 'P') + pits + '_'
                               + dt + '.' * dots + ties)
                elif c.tag == 'Rest':
                    dots = len(c.findall('dot')) + \
                        sum(len(n.findall('dot')) for n in c.findall('Note'))
                    out.append('R_' + (c.findtext('durationType') or 'quarter')
                               + '.' * dots)
            print(f'  M{j + 1}' + (' L=' + mn if mn else '') + ': '
                  + ' '.join(out)[:260])


if __name__ == '__main__':
    main()
