import functions
#import nidaqmx as dx
import mydaq
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit
import time

daq = mydaq.MyDAQ()

#--------------------------------------------------#
# Channel settings
initial_input_channel = 'myDAQ1/ai0'
post_input_channel = 'myDAQ1/ai1'
output_channel = 'myDAQ1/ao0'

# Measurement settings
scale1 = 'log'
calibration_amount = 5
measurement_amount = 5
fs = 100000
freq_amount = 40
min_freq = 20
max_freq = 10000
ampli = 0.5
dur = 0.5
df = 3

daq.set_sample_rate(fs)
# %%
#--------------------------------------------------#
# Calibration Calculating

phase_offsets = []

for _ in range(calibration_amount):
    phase_offset = functions.Functions.calc_phase_dif(
        daq, fs, freq_amount, min_freq,
        max_freq, ampli, dur, df,
        scale=scale1,
        initial_input_channel=initial_input_channel,
        post_input_channel=post_input_channel,
        output_channel=output_channel
    )[0]

    phase_offsets.append(phase_offset)

phase_offsets = np.asarray(phase_offsets)

calibrated_mean = np.angle(np.mean(np.exp(1j * phase_offsets), axis=0))

# %%

freqsa = np.geomspace(min_freq, max_freq, freq_amount)

plt.plot(freqsa, calibrated_mean)
#plt.xscale('log')
plt.show()

# %%



#--------------------------------------------------#
# Transfer Function

magnitude_runs = []
phase_runs = []

for _ in range(measurement_amount):
    magnitude, phase, frequencies = functions.Functions.calculate_power(
        daq, fs, freq_amount, min_freq,
        max_freq, ampli, dur, df,
        calibrated_mean,
        scale=scale1,
        initial_input_channel=initial_input_channel,
        post_input_channel=post_input_channel,
        output_channel=output_channel
    )

    magnitude_runs.append(magnitude)
    phase_runs.append(phase)

magnitude_runs = np.asarray(magnitude_runs)
phase_runs = np.asarray(phase_runs)

mean_magnitude = np.mean(magnitude_runs, axis=0)

mean_phase = np.angle(np.mean(np.exp(1j * phase_runs), axis=0))

# Convert phase from radians to degrees
mean_phase_deg = np.degrees(mean_phase)

# %%


#--------------------------------------------------#
# Error Calculations
std_magnitude = np.std(magnitude_runs, axis=0, ddof=1)
sem_magnitude = std_magnitude / np.sqrt(measurement_amount)

phase_deviations = np.angle(np.exp(1j * (phase_runs - mean_phase)))
std_phase = np.std(phase_deviations, axis = 0, ddof = 1)
sem_phase = std_phase / np.sqrt(measurement_amount)

calibration_deviations = np.angle(np.exp(1j * (phase_offsets - calibrated_mean)))
std_calibration = np.std(calibration_deviations, axis = 0, ddof = 1)
sem_calibration = std_calibration / np.sqrt(calibration_amount)

R = 10e3
C = 9e-9
dR = 0.2e3
dC = 0.2e-9
dF = 0.01 / 100 * frequencies
term = 2*np.pi*frequencies*R*C
theo_err = np.sqrt((dF/frequencies)**2+(dR/R)**2+(dC/C)**2)

sam_theo_mag = term**2/((1+term**2)**(3/2))*theo_err
sem_theo_phase = term/(1+term**2)*theo_err

sem_mag_total = np.sqrt(sem_magnitude**2 + sam_theo_mag**2)
sem_phase_total = np.sqrt(sem_phase**2 + sem_calibration**2 + sem_theo_phase**2)
sem_phase_total_deg = np.degrees(sem_phase_total)

# %%

#--------------------------------------------------#
# Bode plot

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8))

# Magnitude plot
magnitude_db = 20 * np.log10(mean_magnitude)
magnitude_low = mean_magnitude - sem_mag_total
magnitude_high = mean_magnitude + sem_mag_total
magnitude_db_low = 20 * np.log10(magnitude_low)
magnitude_db_high = 20 * np.log10(magnitude_high)
mag_yerr_db = np.asarray([magnitude_db - magnitude_db_low, magnitude_db_high - magnitude_db])

ax1.errorbar(frequencies, magnitude_db, yerr=mag_yerr_db, markersize = 2.5, fmt='o', capsize=3, ecolor = 'red')
ax1.set_xscale('log')
ax1.set_xlabel('Frequency (Hz)')
ax1.set_ylabel('Magnitude (dB)')
ax1.set_title('Experimental Transfer Function Magnitude')
ax1.grid(True, which='both')

# Phase error plot
ax2.errorbar(frequencies, mean_phase_deg, yerr=sem_phase_total_deg, markersize = 2.5, fmt='o', capsize=3, ecolor = 'red')
ax2.set_xscale('log')
ax2.set_xlabel('Frequency (Hz)')
ax2.set_ylabel('Phase (degrees)')
ax2.set_title('Experimental Transfer Function Phase')
ax2.grid(True, which='both')

plt.tight_layout()
plt.show()

fig, ax = plt.subplots(subplot_kw={"projection": "polar"}, figsize=(6, 6))
ax.errorbar(mean_phase, mean_magnitude, yerr = sem_mag_total, xerr = sem_phase_total, capsize = 1, markersize = 2.5, fmt='o', color="darkblue", lw=2, ecolor = 'red')
ax.set_title("Polar Magnitude-Phase Locus", va="bottom")
plt.show()


# %%

#--------------------------------------------------#
# NEW CODE: Curve Fitting for Cutoff Frequency (fc)
#--------------------------------------------------#
def mag_model(f, fc):
  return 1 / np.sqrt(1 + (f / fc) ** 2)


def phase_model(f, fc):
  return -np.arctan(f / fc)


p0_guess = [1 / (2 * np.pi * 10e3 * 10e-9)]

popt_mag, pcov_mag = curve_fit(
    mag_model, frequencies, mean_magnitude, p0=p0_guess
)
fc_fit_mag = popt_mag[0]
fc_err_mag = np.sqrt(pcov_mag[0, 0])

popt_phase, pcov_phase = curve_fit(
    phase_model, frequencies, mean_phase, p0=p0_guess
)
fc_fit_phase = popt_phase[0]
fc_err_phase = np.sqrt(pcov_phase[0, 0])

print(f"Fitted fc (from Magnitude): {fc_fit_mag:.2f} ± {fc_err_mag:.2f} Hz")
print(f"Fitted fc (from Phase):     {fc_fit_phase:.2f} ± {fc_err_phase:.2f} Hz")

fit_freqs = np.geomspace(min_freq, max_freq, 500)
fit_mag = mag_model(fit_freqs, fc_fit_mag)
fit_magnitude_db = 20 * np.log10(fit_mag)
fit_phase = phase_model(fit_freqs, fc_fit_mag)
fit_phase_deg = np.degrees(fit_phase)
#--------------------------------------------------#


#--------------------------------------------------#
# Bode plot (Updated with fit lines)
#--------------------------------------------------#
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8))

# Magnitude plot
magnitude_db = 20 * np.log10(mean_magnitude)
magnitude_low = mean_magnitude - sem_mag_total
magnitude_high = mean_magnitude + sem_mag_total
magnitude_db_low = 20 * np.log10(magnitude_low)
magnitude_db_high = 20 * np.log10(magnitude_high)
mag_yerr_db = np.asarray([
    magnitude_db - magnitude_db_low,
    magnitude_db_high - magnitude_db,
])

ax1.errorbar(
    frequencies,
    magnitude_db,
    yerr=mag_yerr_db,
    markersize=3,
    fmt="o",
    capsize=3,
    ecolor="red",
    label="Data",
)

#--------------------------------------------------#
# NEW CODE: Overlay Magnitude Fit Line
#--------------------------------------------------#
ax1.plot(
    fit_freqs,
    fit_magnitude_db,
    color="orange",
    alpha = 0.9,
    linestyle="--",
    label=f"Fit ($f_c$ = {fc_fit_mag:.1f} Hz)",
)
#--------------------------------------------------#

ax1.set_xscale("log")
ax1.set_xlabel("Frequency (Hz)")
ax1.set_ylabel("Magnitude (dB)")
ax1.set_title("Experimental Transfer Function Magnitude")
ax1.grid(True, which="both")
ax1.legend()

# Phase error plot
ax2.errorbar(
    frequencies,
    mean_phase_deg,
    yerr=sem_phase_total_deg,
    markersize=3,
    fmt="o",
    capsize=3,
    ecolor="red",
    label="Data",
)

#--------------------------------------------------#
# NEW CODE: Overlay Phase Fit Line
#--------------------------------------------------#
ax2.plot(
    fit_freqs,
    fit_phase_deg,
    color="orange",
    alpha = 0.9,
    linestyle="--",
    label=f"Fit ($f_c$ = {fc_fit_phase:.1f} Hz)",
)
#--------------------------------------------------#

ax2.set_xscale("log")
ax2.set_xlabel("Frequency (Hz)")
ax2.set_ylabel("Phase (degrees)")
ax2.set_title("Experimental Transfer Function Phase")
ax2.grid(True, which="both")
ax2.legend()

plt.tight_layout()
plt.show()


#--------------------------------------------------#
# Polar Locus Plot (Updated with fit locus)
#--------------------------------------------------#
fig, ax = plt.subplots(subplot_kw={"projection": "polar"}, figsize=(6, 6))
ax.errorbar(
    mean_phase,
    mean_magnitude,
    yerr=sem_mag_total,
    xerr=sem_phase_total,
    capsize=1,
    markersize=2.5,
    fmt="o",
    color="darkblue",
    lw=2,
    ecolor="red",
    label="Data",
)

#--------------------------------------------------#
# NEW CODE: Overlay Theoretical Fit Locus
#--------------------------------------------------#
ax.plot(
    fit_phase,
    fit_mag,
    color="orange",
    alpha = 0.9,
    linestyle="--",
    lw=1.5,
    label="Theoretical Fit Locus",
)
#--------------------------------------------------#

ax.set_title("Polar Magnitude-Phase Locus", va="bottom")
ax.legend(loc="upper right")
plt.show()

# %%
term1 = -np.arctan(2*np.pi*frequencies*R*C)
rms = np.sqrt(np.mean(np.angle(np.exp(1j*(mean_phase-term1)))))
print(rms*180/np.pi)