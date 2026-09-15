import nidaqmx as dx
import matplotlib.pyplot as plt
import numpy as np
import time

"""
To write data (= voltage(s)) to the MyDAQ, we use the package NiDAQmx.
We will first work through writing data
"""

#%%

# We start a task to write a single output
with dx.Task() as writeTask:
    
    """Now writeTask is everything we need to worry about"""
    # We need to tell the computer where to write to. 
    # Of course, this will be the MyDAQ and to the output AO0.
    writeTask.ao_channels.add_ao_voltage_chan('myDAQ1/ao0')    # MyDAQ2 ipo 1 everywhere
    
    """
    Let's first try to just write a single voltage. Connect a scope to 
    the output (AO0) of the MyDAQ and connect the MyDAQ to the computer
    """
    
    # There are two ways to write,
    
    #1) We define a write task, and start it. 
    myVoltage = 4
    writeTask.write(myVoltage)
    writeTask.start()
    
    #Remember that a task always needs to be closed!
    writeTask.stop()
    
    #2) In one go
    writeTask.write(myVoltage, auto_start=True)
    
    """
    So, as you can see we have just used the writeTask.write() function 
    to write a single output to the MyDAQ If everything is OK you 
    should now see this voltage on the scope?
    """
    
    writeTask.stop()
    
# %%

# Again, we start a task like before
with dx.Task() as writeTask:
    
    # Add your output channel to WriteTask as before.
    writeTask.ao_channels.add_ao_voltage_chan('myDAQ1/ao0')
    
    # We define a sample rate
    rate             = 5 # samples / sec
    
    # Number of samples to write
    samps_per_chan = 50                     # long not needed anymore
    
    # Question: How long will the signal last?
    
    writeTask.timing.cfg_samp_clk_timing(rate, sample_mode = dx.constants.AcquisitionType.FINITE, \
                                         samps_per_chan=samps_per_chan)    
    """The sample_mode is set to FINITE. 
    This means that the MyDAQ expects a FINITE number
    of samples to write, e.g. samps_per_chan.
    
    Sample mode is either dx.constants.AcquisitionType.FINITE or 
    dx.constants.AcquisitionType.CONTINUOUS.
    
    Samps_per_chan specifies the number of samples to generate if in 
    FINITE, or if CONTINUOUS this specifies the buffer size.
    # make sure samps_per_chan is of integer type long (by using long())
    """
    
    # Now everything is set and we can start to write data
    
    # First define the sequence you want to write to the MyDAQ
    stairs = [0.0, 0.0, 1.1, 2.2, 3.3, 4.4, 5.5, 6, 8, 9]

    
    # Then you can simply write it to the MyDAQ like before
    writeTask.write(stairs, auto_start=True)
    
    """This data is now stored on the MyDAQ to be written to the output. 
    This takes however a finite amount of time, since we are writing 
    with finite frequency. We thus wait before closing the connection"""
    time.sleep(samps_per_chan/rate + 0.001)
    writeTask.stop()

# %%

with dx.Task() as writeTask: 
    
    # First, we add both channels to writeTask
    writeTask.ao_channels.add_ao_voltage_chan('myDAQ1/ao0')
    writeTask.ao_channels.add_ao_voltage_chan('myDAQ1/ao1')
    
    # We define a rate
    rate             = 500 # samples / sec
    
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

# %%

with dx.Task() as readTask:
    # Add the correct channel to readTask
    readTask.ai_channels.add_ai_voltage_chan('myDAQ1/ai0')
    
    # Again define the clock settings
    samps_per_chan = 500
    rate = 100000
    
    readTask.timing.cfg_samp_clk_timing(rate, sample_mode = dx.constants.AcquisitionType.FINITE, samps_per_chan=samps_per_chan)
     
    # 1 Channel 1 Sample read:
    data = readTask.read()
    print(data)
    
    # 1 Channel N Samples read:
    data = readTask.read(number_of_samples_per_channel = 100000)
    # print(data)
    plt.figure(1)
    plt.plot(data)
    plt.show()

# %%
    
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
    
# %%
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
        
    writeTask.write(sine, auto_start=True)
    data = readTask.read(number_of_samples_per_channel = 100)
    print(data)
    plt.figure(1)
    plt.plot(data)
    plt.show()
    
    time.sleep(samps_per_chan/rate + 0.001)
    writeTask.stop()