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
man_freqs = []
calibration_amount = 5
measurement_amount = 5
fs = 100000
freq_amount = 40
L = 100e-3 #coil henries
dL = np.nan #error on coil henries
C = 100e-9 #capacitor farads
dC = np.nan #error on capacitor
R = 100 #external resistance
dR = np.nan #error on external resistance
rL = np.nan #coil resistance
Rt = R + rL
Qth = (1 / Rt) * np.sqrt(L / C) #theo quality factor
fth0 = 1 / (2 * np.pi * np.sqrt(L * C)) #theo resonance frequency
min_freq = 0.3 * fth0
max_freq = 3 * fth0
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
        scale=scale1, man_freqs = man_freqs,
        initial_input_channel=initial_input_channel,
        post_input_channel=post_input_channel,
        output_channel=output_channel
    )[0]

    phase_offsets.append(phase_offset)

phase_offsets = np.asarray(phase_offsets)

calibration_mean = np.angle(np.mean(np.exp(1j * phase_offsets), axis=0))

# %%
#--------------------------------------------------#
# Transfer Function

magnitude_runs = []
phase_runs = []

for _ in range(measurement_amount):
    magnitude, phase, frequencies = functions.Functions.calculate_power(
        daq, fs, freq_amount, min_freq,
        max_freq, ampli, dur, df,
        calibration_mean,
        scale=scale1, man_freqs = man_freqs,
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

# %%
#--------------------------------------------------#
# Error Calculations

std_magnitude = np.std(magnitude_runs, axis=0, ddof=1)
sem_magnitude = std_magnitude / np.sqrt(measurement_amount)

phase_deviations = np.angle(np.exp(1j * (phase_runs - mean_phase)))
std_phase = np.std(phase_deviations, axis = 0, ddof = 1)
sem_phase = std_phase / np.sqrt(measurement_amount)

calibration_deviations = np.angle(np.exp(1j * (phase_offsets - calibration_mean)))
std_calibration = np.std(calibration_deviations, axis = 0, ddof = 1)
sem_calibration = std_calibration / np.sqrt(calibration_amount)

sem_mag_total = sem_magnitude
sem_phase_total = np.sqrt(sem_phase**2 + sem_calibration**2)

# %% 
#--------------------------------------------------#
# Creating the fits

mag_fit, fit_freqs, mag_popt, mag_pcov = functions.Functions.fit_bode_func(frequencies, functions.Curvefits.BandpassFilterMag,
                                            mean_magnitude, [fth0, Qth], error = sem_mag_total)
phase_fit, fit_freqs, phase_popt, phase_pcov = functions.Functions.fit_bode_func(frequencies, functions.Curvefits.BandpassFilterPhase,
                                            mean_phase, [fth0, Qth], unwrap_phase = True, error = sem_phase_total)

# %% 
#--------------------------------------------------#
# Plotting stuff

# Raw bode plot
values = functions.Functions.bode_plot(frequencies, mean_magnitude, mean_phase, sem_mag_total,
                                       sem_phase_total)

# Bode plot with fits 
# values = functions.Functions.bode_plot(frequencies, mean_magnitude, mean_phase, sem_mag_total,
#                                        sem_phase_total, mag_fit, functions.Curvefits.BandpassFilterMag, 
#                                        mag_popt, mag_pcov, phase_fit, functions.Curvefits.BandpassFilterPhase, 
#                                        phase_popt, phase_pcov, fit_freqs)

# %%
#--------------------------------------------------#
# Further Analysis

# finding f1 and f2
f1 , s1, f2, s2 = functions.Functions.half_power_frequencies(frequencies, mean_magnitude, sem_mag_total)
print(f"Rising half power freq 'f1' is: {f1} ± {s1:.10f}")
print(f"Falling half power freq 'f2' is: {f2} ± {s2:.10f}")

# Finding bandwith
bandwidth = f2 - f1
bandwidth_error = np.sqrt(s1**2 + s2**2)
print(f'The bandwidth is {bandwidth:.10f} ± {bandwidth_error:.10f}')

#Finding quality factor from bandwidth
f0_meas  = mag_popt[0]
sf0_meas = np.sqrt(mag_pcov[0, 0])
Qbw = f0_meas / bandwidth
Qbw_error = Qbw * np.sqrt((bandwidth_error / bandwidth)**2 + (sf0_meas / f0_meas)**2 + (0.01 / 100)**2)
print(f"Q from bandwidth: {Qbw:.10f} ± {Qbw_error:.10f}")