import nidaqmx as dx
import matplotlib.pyplot as plt
import numpy as np
import time

# To combine reading and writing you will need to put the two together.
with dx.Task('AOTask') as writeTask, dx.Task('AITask') as readTask:
    # Add the correct channel to readTask
    readTask.ai_channels.add_ai_voltage_chan('myDAQ1/ai0')
    # Add your output channel to WriteTask as before.
    writeTask.ao_channels.add_ao_voltage_chan('myDAQ1/ao0')
    
    # Question: How long will the signal last?
    samps_per_chan = 100
    rate = 10

    writeTask.timing.cfg_samp_clk_timing(rate, sample_mode = dx.constants.AcquisitionType.FINITE, \
                                         samps_per_chan=samps_per_chan) 
 
    readTask.timing.cfg_samp_clk_timing(rate, sample_mode = dx.constants.AcquisitionType.FINITE, samps_per_chan=samps_per_chan)

    # 1 Channel N Samples read:
    # stairs = [0.0, 0.0, 1.1, 2.2, 3.3, 4.4, 5.5, 6, 8, 9, 0] 
    
    sine = np.sin(np.linspace(0, samps_per_chan/rate, samps_per_chan))
        #I still don't understand what we're doing with sine thing here. Why are we dividing
        #samps_per_chan by rate?
        
    writeTask.write(sine, auto_start=True)
    data = readTask.read(number_of_samples_per_channel = 100)
    print(data)
    plt.figure(1)
    plt.plot(data)
    plt.show()
    
    time.sleep(samps_per_chan/rate + 0.001)
    writeTask.stop()