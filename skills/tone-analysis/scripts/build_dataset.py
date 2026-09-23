# build_dataset.py — consolidate tone_report/txt_spectrum JSONs into the repo dataset.
# Usage: python build_dataset.py [report_dir] [out_json]
#   report_dir  directory holding <label>_report.json / <label>_txt.json (default: ../reports rel to script)
#   out_json    default: <repo>/research/analysis/alto-recordings-tone-data.json
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))  # scripts -> tone-analysis -> skills -> .opencode -> repo
REPDIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "research", "analysis", "reports")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(REPO, "research", "analysis", "alto-recordings-tone-data.json")

NOTES = {  # label -> (wav file, nominal note, recording method)
    "C5":     ("research/C5.wav", "C5", "free blow, no tuner"),
    "C5_2nd": ("research/C5_2nd_recording.wav", "C5", "tuner loop"),
    "D6":     ("research/D6.wav", "D6", "tuner loop"),
    "G6":     ("research/G6.wav", "G6", "tuner loop"),
}
ET = {"C5": 523.2511, "D6": 1174.659, "G6": 1567.982}
TRIO = ["C5_2nd", "D6", "G6"]  # tuner-verified pitch points for trend fitting

def load(name):
    p = os.path.join(REPDIR, name)
    return json.load(open(p)) if os.path.exists(p) else None

def r2(x, n=4):
    return round(x, n) if isinstance(x, float) else x

def round_rec(d, n=4):
    if isinstance(d, dict):  return {k: round_rec(v, n) for k, v in d.items()}
    if isinstance(d, list):  return [round_rec(v, n) for v in d]
    if isinstance(d, float): return round(d, n)
    return d

measured = {}
for label, (wav, nominal, method) in NOTES.items():
    rep = load(label + "_report.json")
    if not rep:
        print("missing report for", label, "- skipped"); continue
    e = {
        "file": wav, "method": method,
        "duration_s": r2(rep["duration_s"], 3),
        "overall_rms_dbfs": r2(rep["overall_rms_dbfs"], 2),
        "peak_dbfs": r2(rep["peak_dbfs"], 2),
        "pitch": rep["pitch"],
        "envelope": rep["envelope"],
        "timbre": {
            "H2_H8_ratio_re_H1_median": [r2(v) for v in rep["timbre"]["harmonic_ratio_re_H1_median"]],
            "H2_H8_db_re_H1_median": [r2(v, 2) for v in rep["timbre"]["harmonic_db_re_H1_median"]],
            "H1_plateau_rms_dbfs": r2(rep["timbre"]["H1_plateau_rms_dbfs"], 2),
            "evolution_thirds": rep["timbre"]["evolution_thirds"],
        },
        "noise": {
            "bands_rel_H1": rep["noise"]["bands"],
            "evolution_thirds": rep["noise"]["evolution_thirds"],
            "residual_centroid_hz": r2(rep["noise"]["residual_centroid_hz"], 1),
        },
        "inharmonic_islands": rep["inharmonic_islands"],
        "onset": rep["onset"],
    }
    txt = load(label + "_txt.json") or load(label + "_txt_spectrum.json")
    if txt:
        e["txt_snapshot"] = {
            "f0_hz": r2(txt["f0_hz"], 2), "cents_vs_et": r2(txt["cents_vs_et"], 2),
            "H2": r2(txt["harmonics"][0]["ratio_re_H1"]) if txt["harmonics"] else None,
            "H3": r2(txt["harmonics"][1]["ratio_re_H1"]) if len(txt["harmonics"]) > 1 else None,
            "noise_1f_2f_db_rel_H1": r2(txt.get("noise_1f_2f_db_rel_H1"), 2),
        }
    measured[label] = e

def trend(vals):
    pts = [(f, v) for f, v in vals if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if len(pts) < 2: return None
    (f1, v1), (f2, v2) = pts[0], pts[-1]
    if f1 == f2 or f2 <= f1: return None
    return {
        "per_octave": r2((v2 - v1) / (12 * (f2 / f1 - 1)), 3),
        "interp": "linear through measured points; values keyed by f0; small-N, indicative only",
        "points": [[r2(f, 1), r2(v, 4)] for f, v in pts],
    }

def envv(key): return [(measured[l]["pitch"]["median_hz"], measured[l]["envelope"].get(key)) for l in TRIO]
def pitv(key): return [(measured[l]["pitch"]["median_hz"], measured[l]["pitch"].get(key)) for l in TRIO]
def timv(idx): return [(measured[l]["pitch"]["median_hz"], measured[l]["timbre"]["H2_H8_ratio_re_H1_median"][idx]) for l in TRIO]
def noiz(band): return [(measured[l]["pitch"]["median_hz"], measured[l]["noise"]["bands_rel_H1"][band]["db_rel_H1_median"]) for l in TRIO]

trends = {
    "note": "X = recorded median f0 (Hz), tuner-verified trio. The free-blown C5 (‑33.7 cents) is blow-variance evidence, not a trend point.",
    "plateau_level_dbfs": trend(envv("plateau_dbfs")),
    "attack_time_s": trend(envv("attack_to_plateau_s")),
    "attack_overshoot_db": trend(envv("attack_overshoot_db")),
    "breath_wobble_std_pct": trend(envv("breath_wobble_std_pct")),
    "wobble_dominant_hz": trend(envv("wobble_dominant_hz")),
    "wobble_dominant_depth_pct": trend(envv("wobble_dominant_depth_pct")),
    "pitch_wobble_std_cents": trend(pitv("wobble_std_cents")),
    "onset_pitch_glide_cents": trend(pitv("attack_to_plateau_cents")),
    "H2_ratio_re_H1": trend(timv(0)),
    "H3_ratio_re_H1": trend(timv(1)),
    "H4_ratio_re_H1": trend(timv(2)),
    "H5_ratio_re_H1": trend(timv(3)),
    "noise_band_0.85-1.95f0": trend(noiz("0.85-1.95xf0")),
    "noise_band_1.95-3.90f0": trend(noiz("1.95-3.90xf0")),
    "noise_band_3.90-7.00f0": trend(noiz("3.90-7.00xf0")),
    "noise_band_7.00-12.00f0": trend(noiz("7.00-12.00xf0")),
    "noise_residual_centroid_hz": [(measured[l]["pitch"]["median_hz"], measured[l]["noise"]["residual_centroid_hz"]) for l in TRIO],
}

current_model = {
    "note": ("Analytic constants of the CURRENT synth (js/audio.js defaults) at each pitch, for delta "
             "bookkeeping. Offline render comparisons are pending - the headless-Chrome offline-audio "
             "bugs are documented in the tone-analysis skill."),
    "C5": {
        "f0_hz": 523.2511,
        "wave_harmonics_re": [1, 0.06, 0.03, 0.012, 0.006],
        "lp_cutoff_hz": r2(523.2511 * 4.2, 1),
        "air_partial": {"ratio": 2.01, "level": 0.02, "recording_context": "nothing detectable there above ~-48 dB rel H1"},
        "edge_whistle": {"level": [0.035, 0.057], "ratio": [1.012, 1.02], "recording_context": "no stable island 1.01-1.05x f0 (D6 only: ~-40 dB at 1.032xf0)"},
        "vibrato": {"rate": 5.5, "pitch_depth_cents": 6.06, "trem_depth_pct": 5, "delay_s": 0.35,
                    "recording_context": "no periodic vibrato in recordings; slow wobble 4.5-7.3 Hz at 0.5-2.3% depth"},
        "octave_onset_peak": [0.12, 0.2],
        "chiff_peak_C5size_chamber": 0.0127,
        "masterLevel": 0.26,
    },
    "D6": {
        "f0_hz": 1174.659, "hiF": 0.567,
        "lp_cutoff_hz": r2(1174.659 * 4.2, 1),
        "air_level": r2(0.02 * (1 - 0.75 * 0.567), 4),
        "edge_level": r2((0.035 + 0.25 ** 2 * 0.022) * (1 - 0.7 * 0.567), 4),
    },
    "G6": {
        "f0_hz": 1567.982, "hiF": 1.0,
        "lp_cutoff_hz": r2(1567.982 * 4.2, 1),
        "air_level": r2(0.02 * (1 - 0.75), 4),
        "edge_level": r2((0.035 + 0.022) * (1 - 0.7), 4),
    },
}

data = {
    "meta": {
        "generated": "2026-09-17",
        "source": ("user recordings of an alto double ocarina: C5 (free blow + tuner retake), D6, G6; "
                   "same mic gain across files - level differences are real breath-pressure differences"),
        "format": "44100 Hz stereo 16-bit WAV + recorder FFT txt snapshots (2048pt @44.1k)",
        "notes": [
            "No intentional vibrato/tremolo was played; the slow wobble in the recordings is intrinsic/desirable.",
            "Player instability (pitch wobble, attack variance across takes) is a feature to model, not noise to remove.",
            "C5.wav (free blow) is ~34 cents flat with a harder attack (overshoot +4.8 dB, sharp-onset +24.6 cents); tuner takes are in tune (±1.5 cents).",
            "Recording instrument is an alto double; the synth's articulation constants come from Triple Bass chamber data - chamber mapping must be assumed for alto notes.",
            "No bass-register recordings yet: assumptions live in 'extrapolation_assumptions'.",
            "H2/H3 blow-to-blow spread roughly ±3 dB; a single take's H4+ is not reliable to ±few dB.",
        ],
    },
    "measured": round_rec(measured),
    "trends": trends,
    "current_model_constants": current_model,
    "extrapolation_assumptions": {
        "low_register": [
            "H2/H3 strengthen as pitch drops (trio trend already upward downward): expect H2 ~2-5x the C5 value at A3-A4; verify with future bass recordings.",
            "Pitch wobble and slow amplitude wander should GROW downward (C5 takes ~±7-8 cents / ~10% amp; D6/G6 ~±1 cent / 5-8%).",
            "Attack overshoot grows again at low notes (large chambers build pressure slowly): C5 hard blow showed +4.8 dB; assume 2-6 dB with blow-style variance.",
            "Bass-chamber plateau loudness assumed lower than alto mid-register; tune by ear with DEBUG=1 (masterLevel).",
            "Noise bands relative to H1 sit at -26..-30 (band 0.85-1.95f0), rising slightly with pitch; assume flat-to-slightly-rising across the bass range.",
            "No sustained inharmonic edge whistle exists in the recordings (only a faint ~-40 dB one at D6); current synth's edge/air partials are louder than anything measured and should be reduced or randomized per breath.",
        ],
    },
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(data, open(OUT, "w"), indent=1)
print("wrote", OUT)
