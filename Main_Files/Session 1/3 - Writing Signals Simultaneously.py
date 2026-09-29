import nidaqmx as dx
import matplotlib.pyplot as plt
import numpy as np
import time

with dx.Task() as writeTask: 
    
    # First, we add both channels to writeTask, one signal writing to ao0 and the other to ao1.
    writeTask.ao_channels.add_ao_voltage_chan('myDAQ1/ao0')
    writeTask.ao_channels.add_ao_voltage_chan('myDAQ1/ao1')
    
    # We define a rate
    rate = 500 # samples / sec  
    # number of samples to write
    samps_per_chan = 10000
    
    writeTask.timing.cfg_samp_clk_timing(rate, sample_mode = dx.constants.AcquisitionType.FINITE, \
                                         samps_per_chan=samps_per_chan)  
    
    """Everything is set. Instead of passing a list or array to the 
    write function, we now need to pass two of them. One per channel"""
    
    # This writing can be done using lists:
    channel1data = [1.1, 2.2, 3.3]
    channel2data = [1.1, 2.2, 4.4]
    
    # 2 channels , 3 samples per channel
    writeTask.write([channel1data, channel2data], auto_start=True)
    
    time.sleep(samps_per_chan/rate + 0.001)
    
    writeTask.stop()