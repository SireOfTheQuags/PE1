from imports import *

with dx.Task() as readTask:
    # How to read a signal from an oscilloscope using myDAQ
    # Add the correct channel to readTask
    readTask.ai_channels.add_ai_voltage_chan('myDAQ1/ai0')
    
    # Again define the clock settings
    samps_per_chan = 500
    rate = 100000
    # This means we will read a total of 500 samples (500 voltage measurements) with a rate of
    # 100000 samples per second. So these measurements will be done in 5ms.

    
    readTask.timing.cfg_samp_clk_timing(rate, sample_mode = dx.constants.AcquisitionType.FINITE, samps_per_chan=samps_per_chan)
     
    # 1 Channel 1 Sample read:
    data = readTask.read()
    print(data)
    
    # 1 Channel N Samples read:
    data = readTask.read(number_of_samples_per_channel = 100000)
    plt.figure(1)
    plt.plot(data)
    plt.show()   