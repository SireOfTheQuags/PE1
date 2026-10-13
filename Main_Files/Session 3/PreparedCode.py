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
df = None
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


