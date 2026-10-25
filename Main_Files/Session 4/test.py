import functions
#import nidaqmx as dx
import mydaq
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit
import time

daq = mydaq.MYDAQ()

# Channel settings
initial_input_channel = 'myDAQ1/ai0'
post_input_channel = 'myDAQ1/ai1'
output_channel = 'myDAQ1/ao0'

# Measurement settings
scale1 = 'log'
calibration_amount = 3
measurement_amount = 5
freq_amount = 40
calibrated_mean = np.zeros(freq_amount)
fs = 100000
freq_amount = 40
min_freq = 20
max_freq = 10000
ampli = 0.5
dur = 0.5
df = 3

daq.set_sample_rate(fs)

magnitude, phase, frequencies = functions.Functions.calculate_power(
    daq, fs, freq_amount, min_freq,
    max_freq, ampli, dur, df,
    calibrated_mean,
    scale=scale1,
    initial_input_channel=initial_input_channel,
    post_input_channel=post_input_channel,
    output_channel=output_channel
)
