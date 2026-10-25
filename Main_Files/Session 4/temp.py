import functions
#import nidaqmx as dx
import mydaq
import matplotlib.pyplot as plt
import numpy as np
import time

daq = mydaq.MyDAQ()

#--------------------------------------------------#
# Channel settings
initial_input_channel = 'd'
post_input_channel = 'd'
output_channel = 'd'

# Measurement settings
scale1 = 'log'
calibration_amount = 3
measurement_amount = 5
fs = 100000
freq_amount = 40
min_freq = 20
max_freq = 10000
ampli = 0.5
dur = 0.5
df = 3

daq.set_sample_rate(fs)
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

sem_phase_total = np.sqrt(sem_phase**2 + sem_calibration**2)
sem_phase_total_deg = np.degrees(sem_phase_total)

#--------------------------------------------------#
# Bode plot

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8))

# Magnitude plot

magnitude_db = 20 * np.log10(mean_magnitude)
magnitude_low = mean_magnitude - sem_magnitude
magnitude_high = mean_magnitude + sem_magnitude
magnitude_db_low = 20 * np.log10(magnitude_low)
magnitude_db_high = 20 * np.log10(magnitude_high)
mag_yerr_db = np.asarray([magnitude_db - magnitude_db_low, magnitude_db_high - magnitude_db])

ax1.errorbar(frequencies, magnitude_db, yerr=mag_yerr_db, fmt='o', capsize=4)
ax1.set_xscale('log')
ax1.set_xlabel('Frequency (Hz)')
ax1.set_ylabel('Magnitude (dB)')
ax1.set_title('Experimental Transfer Function Magnitude')
ax1.grid(True, which='both')

# Phase error plot
ax2.errorbar(frequencies, mean_phase_deg, yerr=sem_phase_total_deg, fmt='o', capsize=4)
ax2.set_xscale('log')
ax2.set_xlabel('Frequency (Hz)')
ax2.set_ylabel('Phase (degrees)')
ax2.set_title('Experimental Transfer Function Phase')
ax2.grid(True, which='both')

plt.tight_layout()
plt.show()
