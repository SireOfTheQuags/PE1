import nidaqmx as dx
import matplotlib.pyplot as plt
import numpy as np
import time

with dx.Task() as readTask:
    # Now we will add two channels to the readTask
    readTask.ai_channels.add_ai_voltage_chan('myDAQ1/ai0')
    readTask.ai_channels.add_ai_voltage_chan('myDAQ1/ai1')
    
    # Again define the clock settings
    samps_per_chan = 500
    rate = 100000
    
    readTask.timing.cfg_samp_clk_timing(rate, sample_mode = dx.constants.AcquisitionType.FINITE, samps_per_chan=samps_per_chan)
     
    # 2 Channel 1 Sample read:
    data = readTask.read()
    print(data)
    
    # 2 Channel N Samples read:
    data = readTask.read(number_of_samples_per_channel = 100000)
    
    # print(data)
    plt.figure(1)
    plt.plot(data[0]) # Data from the first channel
    plt.plot(data[1]) # Data from the second channel
    plt.show()
    