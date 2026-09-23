# summarize.py — compact comparison table across tone_report JSONs.
# Usage: python summarize.py C5 C5_2nd D6 G6 [--dir report_dir]
import json, sys, os

d = os.path.dirname(os.path.abspath(__file__))
names, args = [], sys.argv[1:]
i = 0
while i < len(args):
    if args[i] == "--dir":
        d = args[i + 1]; i += 2; continue
    names.append(args[i]); i += 1

def rep(name):
    return json.load(open(os.path.join(d, name + "_report.json")))

for n in names:
    r = rep(n)
    p, e, t, nz = r["pitch"], r["envelope"], r["timbre"], r["noise"]
    print(f"== {n}: f0 {p['median_hz']:.1f} Hz ({p['cents_vs_et']:+.1f} c), "
          f"atk {p['attack_to_plateau_cents']:+.1f} c, drift {p['plateau_drift_cents']:+.1f} c, "
          f"wobble {p['wobble_std_cents']:.2f}/{p['wobble_pp_cents']:.1f} c")
    print(f"   env: atk {e['attack_to_plateau_s']*1000:.0f} ms, overshoot {e['attack_overshoot_db']:+.2f} (max {e['attacks_max_overshoot_db']:+.2f}) dB, "
          f"plateau {e['plateau_dbfs']:.1f} dBFS, spread {e['plateau_spread_db']:.2f} dB, "
          f"wob {e['breath_wobble_std_pct']:.1f}% @ {e['wobble_dominant_hz']:.1f} Hz (depth {e['wobble_dominant_depth_pct']:.2f}%)")
    print(f"   H2..H7 dB: {[round(x,1) for x in t['harmonic_db_re_H1_median'][:6]]}, H1 {t['H1_plateau_rms_dbfs']:.1f} dBFS")
    print(f"   noise: " + " ".join(f"{k.split('-')[0]}-{k.split('-')[1][:-5]}:{v['db_rel_H1_median']:+.1f}"
                                  for k, v in nz["bands"].items()))
    print(f"   islands: {r['inharmonic_islands'] or 'none'}  centroid {nz['residual_centroid_hz']:.0f} Hz")
    ev = t["evolution_thirds"]
    print(f"   evolution early/mid/late H2: {ev['early'][0]:.4f}/{ev['mid'][0]:.4f}/{ev['late'][0]:.4f}, "
          f"noise: {nz['evolution_thirds']['early']:+.1f}/{nz['evolution_thirds']['mid']:+.1f}/{nz['evolution_thirds']['late']:+.1f}")
