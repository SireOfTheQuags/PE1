import functions
#import nidaqmx as dx
import mydaq
import matplotlib.pyplot as plt
import numpy as np
import time

fs = 100000
freq_amount = 40
min_freq = 20
max_freq = 10000
ampli = 0.5
dur = 0.5

freqs = np.geomspace(min_freq, max_freq, freq_amount)
samples = int(fs*dur)
t = np.arange(samples) / fs
mydaq.MyDAQ.set_sample_rate(fs)

for freq in freqs:
    sine = ampli*np.sin(2 * np.pi * freq * t)
    data = mydaq.MyDAQ.write_and_read(sine)
    functions.Functions.save_data_to_txt(f"voltage_after_{freq}Hz")
