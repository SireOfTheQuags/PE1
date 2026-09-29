# We start a task to write a single output
import nidaqmx as dx
import matplotlib.pyplot as plt
import numpy as np
import time

with dx.Task() as writeTask:
    
    """Now writeTask is everything we need to worry about"""
    # We need to tell the computer where to write our output to. We're basically telling it to send
    # a signal from this port.
    # Of course, this will be the MyDAQ and to the output AO0.
    writeTask.ao_channels.add_ao_voltage_chan('myDAQ1/ao0')
    
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
 