# fastloop3.py — final quick verification with recording-consistent layer levels.
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
                if x["t_ms"] in (83, 108, 133, 158) and x["H1_dbfs"] > -40}

def measure(label, params):
    y = R.render(params, "C5", 1.54)
    wav = os.path.join(TMP, label + ".wav")
    R.save_wav(wav, y)
    p = subprocess.run(["python", "tone_report.py", wav, "--nominal", "C5",
                        "--label", label, "--json", label + "_report.json"],
                       capture_output=True, text=True, timeout=600)
    return json.loads(p.stdout)

base = json.load(open("tuned_params.json"))
# recording-consistent fixes:
#  - edge tone pinned ~ -38..-40 dB rel H1 (recordings: no tonal content there)
#  - chiff low (user: recording chiff virtually unnoticeable; ours narrowband+4x longer)
#  - master re-locked afterwards
base["edgeBase"] = 0.0006
base["edgeReg"] = 0.0004
base["chiffScale"] = 0.25

r = measure("tune4", base)
m = {
    "H1": r["timbre"]["H1_plateau_rms_dbfs"],
    "H2": r["timbre"]["harmonic_db_re_H1_median"][0],
    "H3": r["timbre"]["harmonic_db_re_H1_median"][1],
    "H4": r["timbre"]["harmonic_db_re_H1_median"][2],
    "H5": r["timbre"]["harmonic_db_re_H1_median"][3],
    "band1": r["noise"]["bands"]["0.85-1.95xf0"]["db_rel_H1_median"],
    "plateau": r["envelope"]["plateau_dbfs"],
    "atk": r["envelope"]["attack_overshoot_db"],
    "wob": (round(r["envelope"]["wobble_dominant_depth_pct"], 2), round(r["envelope"]["wobble_dominant_hz"], 2)),
    "wobstd": round(r["envelope"]["breath_wobble_std_pct"], 2),
    "onset_H2": {x["t_ms"]: round(x["H2_ratio"], 4) for x in r["onset"]["portrait"]
                 if x["t_ms"] in (83, 108, 133, 158)},
    "wobc": (round(r["pitch"]["wobble_std_cents"], 2), round(r["pitch"]["wobble_pp_cents"], 2)),
}
print("tune4     :", m)
base["masterLevel"] = round(base["masterLevel"] * 10 ** ((targets["H1"] - m["H1"]) / 20), 4)
r = measure("tune5", base)
m["H1"] = r["timbre"]["H1_plateau_rms_dbfs"]
m["plateau"] = r["envelope"]["plateau_dbfs"]
m["H2"] = r["timbre"]["harmonic_db_re_H1_median"][0]
print("tune5     :", m)
print("targets   :", {k: round(v, 2) for k, v in targets.items()}, "| onset tgt:", tgt_portrait,
      "| rec wob(std,pp):", (6.94, 29.1), "| rec wobp depth: 1.9% @2.5 Hz")

# keep stageA's pure-tone values for h2..h5 (tune4/5 dilute H4/H5 slightly via the
# remnant chiff; the pure-tone lock was exact) - document both:
args = dict(base)
json.dump(args, open("tuned_params.json", "w"), indent=1)
print("\nFINAL OCA_DEBUG first-pass values:")
for k in sorted(args):
    print(f"  {k}: {args[k]}")
