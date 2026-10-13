import functions
#import nidaqmx as dx
import mydaq
import matplotlib.pyplot as plt
import numpy as np
import time
daq = mydaq.MyDAQ()

#--------------------------------------------#
#--------------------------------------------#
fs = 100000
freq_amount = 40
min_freq = 20
max_freq = 10000
ampli = 0.5
dur = 0.5
df = 3
#--------------------------------------------#
#--------------------------------------------#
freqs = np.geomspace(min_freq, max_freq, freq_amount)
samples = int(fs*dur)
t = np.arange(samples) / fs
daq.set_sample_rate(fs)
#--------------------------------------------#
voltages_before = []
voltages_after = []

for freq in freqs:
    sine = ampli*np.sin(2 * np.pi * freq * t)
    data = daq.write_and_read(sine)
    functions.Functions.save_data_to_txt(data, f"voltage_after_{freq}Hz")
    functions.Functions.save_data_to_txt(sine, f"voltage_before_{freq}Hz")
    voltages_after.append(data)
    voltages_before.append(sine)
#--------------------------------------------#
ffts_before = []
ffts_after = []

for i in voltages_after:
    fft, fbins = functions.Functions.fft(i, fs, True)
    ffts_after.append(fft)

for i in voltages_before:
    fft, fbins = functions.Functions.fft(i, fs, True)
    ffts_before.append(fft)

#--------------------------------------------#
powers_before = []
powers_after = []

for i, fft in enumerate(ffts_after):
    power = functions.Functions.power(fbins, fft, freqs[i], df)
    powers_after.append(power)

for i, fft in enumerate(ffts_before):
    power = functions.Functions.power(fbins, fft, freqs[i], df)
    powers_before.append(power)

#--------------------------------------------#

power_before_dict = dict(zip(freqs, powers_before))
print(power_before_dict)
power_after_dict = dict(zip(freqs, powers_after))
print(power_after_dict)


# %%

powers_before = np.asarray(powers_before)
powers_after = np.asarray(powers_after)
H = np.sqrt(powers_after/powers_before)

Hdb = 20*np.log10(H)

H_std = 0.000953
Hdb_std = Hdb_std = (20 / np.log(10)) * (H_std / H)

from scipy.optimize import curve_fit
def model(f, fc):
    return 1 / np.sqrt(1+(f/fc)**2)

poptH, pcovH = curve_fit(model, freqs, H, p0=[1770])
poptHdb, pcovHdb = curve_fit(model, freqs, Hdb, p0=[1770])
fcH_fit = poptH[0]
fcHdb_fit = poptHdb[0]
fcH_uncertainty = np.sqrt(pcovH[0, 0])
fcHdb_uncertainty = np.sqrt(pcovHdb[0, 0])
print(fcH_uncertainty)
print(fcHdb_uncertainty)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))


ax1.errorbar(freqs, H, yerr = H_std, fmt='o', capsize=3)
ax1.plot(freqs, model(freqs, fcH_fit), label="Fit")
ax1.set_xscale("log")
ax1.legend()
ax1.set_title("Transfer Function")
ax1.set_xlabel("Frequencies (Hz)")
ax1.set_ylabel("H (unitless)")

ax2.errorbar(freqs, Hdb, yerr = Hdb_std, fmt='o', capsize=3)
ax2.plot(freqs, model(freqs, fcHdb_fit), label ="Fit")
ax2.set_xscale("log")
ax2.legend()
ax2.set_title("Transfer Function in dB")
ax2.set_xlabel("Frequencies (Hz)")
ax2.set_ylabel("H (dB)")

plt.tight_layout()
plt.show()
# %%

powers_before = np.asarray(powers_before)
powers_after = np.asarray(powers_after)
H = np.sqrt(powers_after/powers_before)

Hdb = 20*np.log10(H)

H_std = 0.08
Hdb_std = Hdb_std = (20 / np.log(10)) * (H_std / H)
Hdb_std = 0.5

# Define the decibel version of your model
def model_db(f, fc):
  # You can also write this as: -10 * np.log10(1 + (f/fc)**2)
  return 20 * np.log10(1 / np.sqrt(1 + (f / fc) ** 2))


# Use the correct model for the dB fit
poptHdb, pcovHdb = curve_fit(model_db, freqs, Hdb, p0=[1770])
fcHdb_fit = poptHdb[0]
fcHdb_uncertainty = np.sqrt(pcovHdb[0, 0])

print("fc (dB):", fcHdb_fit, "±", fcHdb_uncertainty)

# --- Update your plotting for ax2 ---
fig, ax2 = plt.subplots(figsize=(12, 5))

ax2.errorbar(freqs, Hdb, yerr=Hdb_std, fmt="o", capsize=3)
ax2.plot(
    freqs, model_db(freqs, fcHdb_fit), label="Fit"
)  # <-- Use model_db here!
ax2.set_xscale("log")
ax2.legend()
ax2.set_title("Transfer Function in dB")
ax2.set_xlabel("Frequencies (Hz)")
ax2.set_ylabel("H (dB)")

plt.tight_layout()
plt.show()

