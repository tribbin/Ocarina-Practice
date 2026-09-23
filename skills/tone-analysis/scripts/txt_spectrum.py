# txt_spectrum.py — harmonic table from a recorder FFT txt snapshot.
# Usage: python txt_spectrum.py <txt> [--nominal C5] [--json out.json]
import sys, json
import numpy as np

def note_hz(n):
    m = {"C":0,"Cs":1,"D":2,"Ds":3,"E":4,"F":5,"Fs":6,"G":7,"Gs":8,"A":9,"As":10,"B":11}
    return 440.0 * 2 ** ((m[n[:-1]] + (int(n[-1])+1)*12 - 69) / 12)

path = sys.argv[1]
nominal = "C5"; jout = None
args = sys.argv[2:]
for i, a in enumerate(args):
    if a == "--nominal": nominal = args[i+1]
    if a == "--json": jout = args[i+1]

rows = open(path).read().strip().split("\n")[1:]
fx = np.array([float(r.split("\t")[0]) for r in rows])
lx = np.array([float(r.split("\t")[1]) for r in rows])
f_nom = note_hz(nominal)
arr = np.where((fx > f_nom*0.85) & (fx < f_nom*1.15))[0]
h1bin = arr[int(np.argmax(lx[arr]))]
a_, b_, c_ = lx[h1bin-1], lx[h1bin], lx[h1bin+1]
d = 0.5*(a_-c_)/(a_-2*b_+c_)
bwh = fx[1]-fx[0]
f0t = fx[h1bin] + d*bwh
h1v = b_ - 0.25*(a_-c_)*d

res = {"file": path, "f0_hz": float(f0t), "cents_vs_et": float(1200*np.log2(f0t/f_nom)),
       "H1_db_abs": float(h1v), "harmonics": []}
k = 1
while True:
    k += 1
    target_bin = k*(h1bin+0)/1.0
    lo = int(0.955*k*h1bin); hi = int(1.045*k*h1bin)+1
    if hi >= len(fx) or k*1.045*f0t > fx[-1]: break
    kk = lo + int(np.argmax(lx[lo:hi]))
    if kk <= 0 or kk >= len(lx)-1: break
    aa, bb, cc = lx[kk-1], lx[kk], lx[kk+1]
    dd = 0.5*(aa-cc)/(aa-2*bb+cc)
    lv = bb - 0.25*(aa-cc)*dd
    res["harmonics"].append({"H": k, "freq_hz": float(fx[0]+(kk+dd)*bwh),
                             "db_abs": float(lv), "ratio_re_H1": float(10**((lv-h1v)/20))})
bet = (fx > f0t*1.06) & (fx < f0t*1.94)
res["noise_1f_2f_db_abs"] = float(np.median(lx[bet]))
res["noise_1f_2f_db_rel_H1"] = float(np.median(lx[bet])-h1v)
bet2 = (fx > f0t*2.1) & (fx < f0t*3.9)
res["noise_2f_4f_db_rel_H1"] = float(np.median(lx[bet2])-h1v)
high = (fx > 6000) & (fx < 21000)
res["hf_floor_db_abs"] = float(np.median(lx[high]))
s = json.dumps(res, indent=1)
print(s)
if jout: open(jout, "w").write(s)
