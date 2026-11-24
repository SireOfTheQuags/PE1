# demo_part2_plot.py  --  standalone, fake data, no DAQ or functions.py needed
import numpy as np
import matplotlib.pyplot as plt

rng = np.random.default_rng(1)
demo_f = np.geomspace(20, 10000, 40)

# Fake transfer functions: bandpass black box (f0 = 1.5 kHz, Q = 3) and the RC low-pass (fc ~ 1.77 kHz)
x = demo_f / 1500
H_bb = 1 / (1 + 1j * 3 * (x - 1 / x))
H_rc = 1 / (1 + 1j * demo_f / 1768)
H_pred = H_bb * H_rc

def make(H, rel_noise=0.01, phase_noise=0.03):
    M = np.abs(H) * (1 + rng.normal(0, rel_noise, demo_f.size))
    phi = np.angle(np.exp(1j * (np.angle(H) + rng.normal(0, phase_noise, demo_f.size))))
    return dict(f=demo_f, M=M, phi=phi,
                sM=0.01 * M + 1e-4, sphi=np.full(demo_f.size, 0.03))

# "Loading": RC -> BB is 15% lower in magnitude and shifted by 0.15 rad
H_loaded = H_pred * 0.85 * np.exp(-1j * 0.15)

demo_data = {
    "BB>RC": make(H_pred),
    "RC>BB": make(H_loaded),
    "pred":  make(H_pred, rel_noise=0.005, phase_noise=0.02),
}

# --- the plot code from your Part 2 (dots only), using demo_data ---
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8))
for key, lab in [("BB>RC", "BB -> RC"), ("RC>BB", "RC -> BB"), ("pred", "Prediction")]:
    d = demo_data[key]
    ax1.errorbar(d["f"], 20*np.log10(d["M"]), yerr=(20/np.log(10))*d["sM"]/d["M"],
                 fmt='o', ms=3, capsize=2, label=lab)
    ax2.errorbar(d["f"], np.degrees(np.unwrap(d["phi"])), yerr=np.degrees(d["sphi"]),
                 fmt='o', ms=3, capsize=2, label=lab)
for ax, yl in ((ax1, "Magnitude (dB)"), (ax2, "Phase (degrees)")):
    ax.set_xscale('log'); ax.set_xlabel("Frequency (Hz)"); ax.set_ylabel(yl)
    ax.grid(True, which='both'); ax.legend()
ax2.set_title('Experimental Transfer Function Phase')
ax1.set_title('Experimental Transfer Function Magnitude')
plt.tight_layout()
plt.show()