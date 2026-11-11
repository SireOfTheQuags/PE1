import functions
import mydaq
import matplotlib.pyplot as plt
import numpy as np
import time
import importlib
daq = mydaq.MyDAQ()

## MAKE SURE THAT HE CALIBRATION IS WITHOUT THE CIRCUIT
## filter 15 is bandpass, filter 2 low pass, filter 8  high pass 
# CONFIDENTLY: 12 IS FIRST ORDER LOW PASS
#--------------------------------------------------#
# Channel settings
initial_input_channel = 'myDAQ1/ai0'
post_input_channel = 'myDAQ1/ai1'
output_channel = 'myDAQ1/ao0'

# Component settings
L = 100e-3       # Coil inductance [H]
dL = np.nan      # Coil inductance uncertainty [H]
C = 100e-9       # Capacitor capacitance [F]
dC = np.nan      # Capacitance uncertainty [F]
R = 100          # External resistance [Ohm]
dR = np.nan      # External resistance uncertainty [Ohm]
rL = 1           # Coil resistance [Ohm]
drL = dR         # Coil resistance uncertainty [Ohm]
Rt = R + rL      # Total resistance circuit [Ohm]

# Some short calculations
fth0 = 1 / (2 * np.pi * np.sqrt(L * C))  # Theoretical resonance frequency [Hz]
Qth = (1 / Rt) * np.sqrt(L / C)          # Theoretical quality factor

# Measurement settings
fs = 100000      # Sampling frequency [samples/s]
dur = 0.5        # Recording duration [s]
ampli = 0.5      # Input amplitude [V]
df = 3           # Frequency window for integration [Hz]
min_freq = 20       # Minimum measurement frequency [Hz]
max_freq = 40000    # Maximum measurement frequency [Hz]
freq_amount = 40    # Number of measurement frequencies
scale1 = 'log'      # Frequency spacing: 'log' or 'linear'
man_freqs = []      # Optional manually specified frequencies [Hz]
calibration_amount = 2  # Number of phase calibration measurements. NEEDS TO BE MINIMUM OF 2, OTHERWISE DIVISION BY ZERO HAPPENS.
measurement_amount = 2  # Number of circuit measurements. NEEDS TO BE MINIMUM OF 2, OTHERWISE DIVISION BY ZERO HAPPENS.

# Curvefit settings
    #! TO SELECT THE KIND OF FIT YOU WANT, YOU HAVE TO CHANGE IT IN THE "Creating the fits" SECTION DOWN BELOW !#
ini_guess_mag = [] # Initial guess for magnitude fit. Change to "None" to not pass anything.
ini_guess_phase = [] # Initial guess for phase fit. Change to "None" to not pass anything.

daq.set_sample_rate(fs)

# %%
#--------------------------------------------------#
# Phase Calibration Calculation

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
# Error calculations based solely on repeat measurements

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

# Need to reload because otherwise changes for R and Rtot won't be reflected. SELECT THE FIT TYPE HERE.
importlib.reload(functions)
fit_type_mag = functions.FitCurves.BandpassFilterMag
fit_type_phase = functions.FitCurves.BandpassFilterPhase

# Here the fits are created
mag_fit, fit_freqs, mag_popt, mag_pcov = functions.Functions.fit_bode_func(frequencies, fit_type_mag,
                                            mean_magnitude, ini_guess_mag, error = sem_mag_total)
phase_fit, fit_freqs, phase_popt, phase_pcov = functions.Functions.fit_bode_func(frequencies, fit_type_phase,
                                            mean_phase, ini_guess_phase, unwrap_phase = True, error = sem_phase_total)

# %% 
#--------------------------------------------------#
# Raw bode plot

values = functions.Functions.bode_plot(frequencies, mean_magnitude, mean_phase, sem_mag_total,
                                        sem_phase_total)

# %%
#--------------------------------------------------#
# Bode plot with fits

# sem_mag_total[:] = 0
# sem_phase_total[:] = 0

values = functions.Functions.bode_plot(frequencies, mean_magnitude, mean_phase, sem_mag_total,
                                        sem_phase_total, mag_fit, fit_type_mag, 
                                        mag_popt, mag_pcov, phase_fit, fit_type_phase, 
                                        phase_popt, phase_pcov, fit_freqs)

# %%
#--------------------------------------------------#
# Further Analysis

# finding f1 and f2
f1 , s1, f2, s2 = functions.Functions.half_power_frequencies(frequencies, mean_magnitude, sem_mag_total)
print(f"Rising half power freq 'f1' is: {f1} ± {s1:.4g}")
print(f"Falling half power freq 'f2' is: {f2} ± {s2:.4g}")

# Finding bandwith
bandwidth = f2 - f1
bandwidth_error = np.sqrt(s1**2 + s2**2)
print(f'The bandwidth is {bandwidth:.6g} ± {bandwidth_error:.4g}')

#Finding quality factor from bandwidth
f0_meas  = mag_popt[0]
sf0_meas = np.sqrt(mag_pcov[0, 0])
Qbw = f0_meas / bandwidth
Qbw_error = Qbw * np.sqrt((bandwidth_error / bandwidth)**2 + (sf0_meas / f0_meas)**2 + (0.01 / 100)**2)
print(f"Q from bandwidth: {Qbw:.6g} ± {Qbw_error:.4g}")

# %%
#--------------------------------------------------#
# Acceptance tests: RMS difference between data and theory

w = 2 * np.pi * frequencies
X = w * L - 1 / (w * C)                      # net reactance

M_th   = R / np.sqrt(Rt**2 + X**2)           # theoretical magnitude
phi_th = -np.arctan2(X, Rt)                  # theoretical phase (rad)

# Magnitude
rms_M = np.sqrt(np.mean((mean_magnitude - M_th)**2))

# Phase
phase_diff = np.angle(np.exp(1j * (mean_phase - phi_th)))
rms_phi = np.sqrt(np.mean(phase_diff**2))
rms_phi_deg = np.degrees(rms_phi)

print(f"RMS_M   = {rms_M:.6g}   (limit 0.1)")
print(f"RMS_phi = {rms_phi_deg:.6g} deg   (limit 10 deg)")