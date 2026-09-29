import nidaqmx as dx
import matplotlib.pyplot as plt
import numpy as np
import time

class MyDAQ:

    def __init__(self):

        self.rate = 500


    # %%
    # Set sample rate

    def set_sample_rate(self, rate):

        self.rate = rate


    # %%
    # Generate an arbitrary signal

    def generate_signal(self, voltages):

        with dx.Task() as writeTask:

            # Add output channel
            writeTask.ao_channels.add_ao_voltage_chan('myDAQ1/ao0')

            # Number of samples
            samps_per_chan = len(voltages)

            # Define sample rate
            writeTask.timing.cfg_samp_clk_timing(
                self.rate,
                sample_mode=dx.constants.AcquisitionType.FINITE,
                samps_per_chan=samps_per_chan
            )

            # Write signal
            writeTask.write(voltages, auto_start=True)

            # Wait until signal is finished
            time.sleep(samps_per_chan / self.rate + 0.001)

            writeTask.stop()


    # %%
    # Generate a sine wave

    def generate_sine(
        self,
        frequency,
        amplitude,
        phase_shift,
        offset,
        duration
    ):

        # Number of samples
        samps_per_chan = int(self.rate * duration)

        # Time array
        t = np.arange(samps_per_chan) / self.rate

        # Sine wave
        voltages = (
            amplitude
            * np.sin(2 * np.pi * frequency * t + phase_shift)
            + offset
        )

        # Write sine wave
        self.generate_signal(voltages)


    # %%
    # Record voltage signal

    def record_voltage(self, duration):

        with dx.Task() as readTask:

            # Add input channel
            readTask.ai_channels.add_ai_voltage_chan('myDAQ1/ai0')

            # Number of samples
            samps_per_chan = int(self.rate * duration)

            # Define sample rate
            readTask.timing.cfg_samp_clk_timing(
                self.rate,
                sample_mode=dx.constants.AcquisitionType.FINITE,
                samps_per_chan=samps_per_chan
            )

            # Read data
            data = readTask.read(
                number_of_samples_per_channel=samps_per_chan
            )

            readTask.stop()

        return data


    # %%
    # Get time array

    def get_time(self, data):

        t = np.arange(len(data)) / self.rate

        return t


    # %%
    # Write and read simultaneously

    def write_and_read(self, voltages):

        with dx.Task('AOTask') as writeTask, dx.Task('AITask') as readTask:

            # Add input channel
            readTask.ai_channels.add_ai_voltage_chan('myDAQ1/ai0')

            # Number of samples
            samps_per_chan = len(voltages)

            # Define sample rate
            readTask.timing.cfg_samp_clk_timing(
                self.rate,
                sample_mode=dx.constants.AcquisitionType.FINITE,
                samps_per_chan=samps_per_chan
            )

            # Add output channel
            writeTask.ao_channels.add_ao_voltage_chan('myDAQ1/ao0')

            # Define sample rate
            writeTask.timing.cfg_samp_clk_timing(
                self.rate,
                sample_mode=dx.constants.AcquisitionType.FINITE,
                samps_per_chan=samps_per_chan
            )

            # Start reading
            readTask.start()

            # Write signal
            writeTask.write(voltages, auto_start=True)

            # Read signal
            data = readTask.read(
                number_of_samples_per_channel=samps_per_chan
            )

            # Wait until writing is finished
            time.sleep(samps_per_chan / self.rate + 0.01)

            writeTask.stop()

        return data

def magnorm(signal):
    """
        Turns magnitude normalised FFT back into signal
    """    
    FFT = np.fft.fft(signal)
    maggie = FFT/np.abs(FFT)
    return np.fft.ifft(maggie)

def phasenorm(signal):
    """
        Turns phase normalised FFT back into signal
    """   
    FFT = np.fft.fft(signal)
    phazy = FFT * np.exp(1j*-np.angle(FFT))
    return np.fft.ifft(phazy)