import matplotlib.pyplot as plt
import numpy as np


class Functions:

    # Takes FFT of a signal, normalizes its magnitude and turns it back into a signal.
    @staticmethod
    def magnorm(signal):    
        FFT = np.fft.fft(signal)
        maggie = np.abs(FFT)
        maggie[maggie == 0] = 1
        return np.fft.ifft(FFT/maggie).real


    # Takes FFT of a signal, normalizes its phase and turns it back into a signal.
    @staticmethod
    def phasenorm(signal):
        FFT = np.fft.fft(signal)
        phazy = np.abs(FFT)
        return np.fft.ifft(phazy).real


    # Plot a signal in either the time or frequency domain.
    @staticmethod
    def plot(signal, fs, domain="time",
            xlabel=None, ylabel=None,
            xlim=None, ylim=None,
            scale="linear", title=None,
            normalize=False):

        signal = np.asarray(signal)
        n = len(signal)

        fig, ax = plt.subplots()

        if domain == "time":
            x = np.arange(n) / fs

            ax.plot(x, signal)
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)

        elif domain == "frequency":
            FFT = np.fft.fft(signal)
            frequencies = np.fft.fftfreq(n, d=(1 / fs))

            spectrum = np.abs(FFT)

            if normalize:
                spectrum = spectrum / n
                spectrum[1:n//2] *= 2

            mask = frequencies >= 0

            ax.plot(frequencies[mask], spectrum[mask])

            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)

            if xlim is None:
                ax.set_xlim(0, fs / 2)

        else:
            raise ValueError("domain must be 'time' or 'frequency'")

        if xlim is not None:
            ax.set_xlim(xlim)
        if ylim is not None:
            ax.set_ylim(ylim)

        if scale == "linear":
            ax.set_xscale("linear")
            ax.set_yscale("linear")
        elif scale == "loglog":
            ax.set_xscale("log")
            ax.set_yscale("log")
        elif scale == "semilogx":
            ax.set_xscale("log")
            ax.set_yscale("linear")
        elif scale == "semilogy":
            ax.set_xscale("linear")
            ax.set_yscale("log")
        else:
            raise ValueError("scale must be 'linear', 'loglog', 'semilogx', or 'semilogy'")

        if title is not None:
            ax.set_title(title)

        ax.grid(True)
        plt.show()