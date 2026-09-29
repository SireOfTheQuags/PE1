import nidaqmx as dx
import matplotlib.pyplot as plt
import numpy as np
import time
import matplotlib.pyplot as plt


class Functions:

    # Turns magnitude normalised FFT back into signal
    def magnorm(signal):    
        FFT = np.fft.fft(signal)
        maggie = FFT/np.abs(FFT)
        return np.fft.ifft(maggie)


    # Turns phase normalised FFT back into signal
    def phasenorm(signal):
        FFT = np.fft.fft(signal)
        phazy = FFT * np.exp(1j*-np.angle(FFT))
        return np.fft.ifft(phazy)