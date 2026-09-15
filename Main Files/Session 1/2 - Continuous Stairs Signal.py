from imports import *

# Again, we start a task like before
with dx.Task() as writeTask:
    
    # Add your output channel to WriteTask as before.
    writeTask.ao_channels.add_ao_voltage_chan('myDAQ1/ao0')
    
    # We define a sample rate
    rate = 5 # samples / sec
    # Number of samples to write
    samps_per_chan = 50

    
    writeTask.timing.cfg_samp_clk_timing(rate, sample_mode = dx.constants.AcquisitionType.FINITE, \
                                         samps_per_chan=samps_per_chan)    
    """The sample_mode is set to FINITE. 
    This means that the MyDAQ expects a FINITE number
    of samples to write, e.g. samps_per_chan.
    
    Sample mode is either dx.constants.AcquisitionType.FINITE or 
    dx.constants.AcquisitionType.CONTINUOUS.
    
    Samps_per_chan specifies the number of samples to generate if in 
    FINITE, or if CONTINUOUS this specifies the buffer size.
    """
    
    # Now everything is set and we can start to write data
    
    # First define the voltage sequence you want to write to the MyDAQ
    stairs = [0.0, 0.0, 1.1, 2.2, 3.3, 4.4, 5.5, 6, 8, 9]

    
    # Then you can simply write it to the MyDAQ like before
    writeTask.write(stairs, auto_start=True)
    
    """This data is now stored on the MyDAQ to be written to the output. 
    This takes however a finite amount of time, since we are writing 
    with finite frequency. We thus wait before closing the connection"""
    time.sleep(samps_per_chan/rate + 0.001)
    writeTask.stop()
