# fastloop2.py — staged decoupled tuning: no cross-talk between layers.
# Stage A: pure tone (h1..h5, master) with all layers off
# Stage B: chiff scale from the burst target
# Stage C: edge level from the sustained band-1 target
# Stage D: octave-onset level from the 83 ms portrait point
# Stage E: final combined verify + print OCA_DEBUG values
import json, os, subprocess, math
import numpy as np
import synth_replica as R

TMP = r"C:\Users\tribb\AppData\Local\Temp\opencode"
os.chdir(TMP)

T = json.load(open("C5_2nd_report.json"))
T_HDB = T["timbre"]["harmonic_db_re_H1_median"]
targets = {
    "H1": T["timbre"]["H1_plateau_rms_dbfs"],
    "H2": T_HDB[0], "H3": T_HDB[1], "H4": T_HDB[2], "H5": T_HDB[3],
    "band1": T["noise"]["bands"]["0.85-1.95xf0"]["db_rel_H1_median"],
    "plateau": T["envelope"]["plateau_dbfs"],
}
tgt_portrait = {x["t_ms"]: x["H2_ratio"] for x in T["onset"]["portrait"]
                if x["t_ms"] in (33, 58, 83, 108, 133, 158) and x["H1_dbfs"] > -40}

def measure(label, params):
    y = R.render(params, "C5", 1.54)
    wav = os.path.join(TMP, label + ".wav")
    R.save_wav(wav, y)
    p = subprocess.run(["python", "tone_report.py", wav, "--nominal", "C5",
                        "--label", label, "--json", label + "_report.json"],
                       capture_output=True, text=True, timeout=600)
    r = json.loads(p.stdout)
    return r, {
        "H1": r["timbre"]["H1_plateau_rms_dbfs"],
        "H2": r["timbre"]["harmonic_db_re_H1_median"][0],
        "H3": r["timbre"]["harmonic_db_re_H1_median"][1],
        "H4": r["timbre"]["harmonic_db_re_H1_median"][2],
        "H5": r["timbre"]["harmonic_db_re_H1_median"][3],
        "band1": r["noise"]["bands"]["0.85-1.95xf0"]["db_rel_H1_median"],
        "plateau": r["envelope"]["plateau_dbfs"],
        "atk": r["envelope"]["attack_overshoot_db"],
        "onset_H2": {x["t_ms"]: round(x["H2_ratio"], 4) for x in r["onset"]["portrait"]
                     if x["t_ms"] in (33, 58, 83, 108, 133, 158)},
        "wob": (r["envelope"]["wobble_dominant_depth_pct"], r["envelope"]["wobble_dominant_hz"]),
        "wobp_std": r["envelope"]["breath_wobble_std_pct"],
    }

base = {
    "h1": 1.0, "h2": 0.006, "h3": 0.005, "h4": 0.0008, "h5": 0.001,
    "vibDepth": 0.0, "tremDepth": 0.0,
    "masterLevel": 0.14, "airLevel": 0.0, "edgeBase": 0.0, "chiffScale": 0.4,
    "otBase": 0.0, "otEffort": 0.0,
}

# ---- Stage A: pure tone ----
r, m = measure("stageA_pure", base)
db = lambda d: 10 ** (d / 20)
for hk, key in (("H2", "h2"), ("H3", "h3"), ("H4", "h4"), ("H5", "h5")):
    d = targets[hk] - m[hk]
    base[key] = round(max(base[key] * db(d), 1e-9), 7)
    print(f"stageA {key}: measured {m[hk]:.1f} dB, target {targets[hk]:.1f} -> {base[key]}")
base["masterLevel"] = round(base["masterLevel"] * db(targets["H1"] - m["H1"]), 4)
print(f"stageA masterLevel -> {base['masterLevel']}")
r, m = measure("stageA2_pure", base)
print("stageA verify:", {k: round(m[k], 2) for k in ("H1", "H2", "H3", "H4", "H5")})

# ---- Stage B: chiff held low (user listened: replica chiff reads much louder
# than the recording's brief broadband swipe because our length is 3-5x longer
# for the bass chamber; length is a code constant, so keep the scale small) ----
rec_burst = [x["db_rel_plateau_H1"] for x in T["onset"]["burst_profile"]][:6]
rec_peak = max(x for x in rec_burst[:4])
c = 0.4
p2 = dict(base); p2["chiffScale"] = c
r, m = measure("stageB_chiff", p2)
burst2 = [x["db_rel_plateau_H1"] for x in r["onset"]["burst_profile"]][:5]
peak2 = max(burst2[:3])
base["chiffScale"] = c
print(f"stageB chiffScale held at {c} (burst peak {peak2:+.1f} dB vs rec {rec_peak:+.1f} dB; "
      f"our burst is narrowband and ~4x longer, so it must sit below the rec metric)")

# ---- Stage C: edge tone level from sustained band-1 target ----
p3 = dict(base); p3["edgeBase"] = 0.035; p3["edgeReg"] = 0.022
r, m = measure("stageC_edge", p3)
b1_only_edge = m["band1"]
# assume band1 is now dominated by edge tone; dB-scale the level to the target
delta = targets["band1"] - b1_only_edge
fb = db(delta)
p3["edgeBase"] = round(max(0.0, min(0.2, p3["edgeBase"] * fb)), 5)
p3["edgeReg"] = round(max(0.0, min(0.1, p3["edgeReg"] * fb)), 5)
r, m = measure("stageC2_edge", p3)
base["edgeBase"] = p3["edgeBase"]; base["edgeReg"] = p3["edgeReg"]
print(f"stageC edge -> base {p3['edgeBase']} reg {p3['edgeReg']} "
      f"(band1 {m['band1']:+.1f} vs tgt {targets['band1']:+.1f}, wob depth {m['wob'][0]:.1f}% @ {m['wob'][1]:.1f} Hz)")

# ---- Stage D: octave onset ----
p4 = dict(base); p4.update(otBase=0.01, otEffort=0.008, otNoise=0.35)
r, m = measure("stageD_ot", p4)
ours83 = m["onset_H2"].get(83) or m["onset_H2"].get(58) or m["onset_H2"].get(33)
tgt83 = tgt_portrait.get(83) or tgt_portrait.get(58) or tgt_portrait.get(33)
if ours83 and tgt83:
    d = 20 * math.log10(max(tgt83, 1e-5) / max(ours83, 1e-5))
    p4["otBase"] = round(max(0.0, p4["otBase"] * db(min(d, 8))), 5)
    p4["otEffort"] = round(max(0.0, p4["otEffort"] * db(min(d, 8))), 5)
    r, m = measure("stageD2_ot", p4)
base.update({"otBase": p4.get("otBase", 0), "otEffort": p4.get("otEffort", 0), "otNoise": 0.35})
print(f"stageD ot -> base {base.get('otBase')} effort {base.get('otEffort')} "
      f"(onset H2 {m['onset_H2']} vs tgt {tgt_portrait})")

# ---- Stage E: combined final + master re-set (edge may bleed into H1 window) ----
r, m = measure("stageE_final", base)
base["masterLevel"] = round(base["masterLevel"] * db(targets["H1"] - m["H1"]), 4)
r, m = measure("stageE2_final", base)
print("final:",
      {k: round(m[k], 2) for k in ("H1", "H2", "H3", "H4", "H5", "band1", "plateau")},
      "atk", round(m["atk"], 2), "wob", m["wob"], "wobstd", round(m["wobp_std"], 1))
print("targets:", {k: round(v, 2) for k, v in targets.items()},
      "onset tgt:", tgt_portrait)

json.dump(base, open(os.path.join(TMP, "tuned_params.json"), "w"), indent=1)
print("\nFINAL OCA_DEBUG values:")
for k in sorted(base):
    print(f"  {k}: {base[k]}")
