import matplotlib.pyplot as plt
import numpy as np
from scipy import integrate
from scipy import stats
from tqdm.auto import tqdm


class Functions:

    # Takes FFT of a signal, normalizes its magnitude and turns it back into a signal.
    # Spectral Whitening.
    @staticmethod
    def magnorm(signal):    
        FFT = np.fft.fft(signal)
        maggie = np.abs(FFT)
        maggie[maggie == 0] = 1
        return np.fft.ifft(FFT/maggie).real


    # Takes FFT of a signal, destroys its phase and turns it back into a signal.
    @staticmethod
    def phasenorm(signal):
        FFT = np.fft.fft(signal)
        phazy = np.abs(FFT)
        return np.fft.ifft(phazy).real


    #Calculate FFT. You can choose to normalize it.
    @staticmethod
    def fft(signal, fs, normalize=False):
        n = len(signal)
        fft_val =  np.fft.rfft(signal)
        frequencies = np.fft.rfftfreq(n, d=(1 / fs))
        if n % 2 == 0:
           fft_val[1:-1] *= 2 
        else:
            fft_val[1:] *= 2
        if normalize:  
            fft_val = fft_val / n
        return fft_val, frequencies


    # Calculates the signal power around a specific frequency. If you want a single
    # frequency, just make min_freq = max_freq and freq_amount = 1.
    @staticmethod   
    def calculate_power(daq, fs, freq_amount, min_freq, 
                          max_freq, amplitude, 
                          duration, df, scale = "linear", normalize = True, 
                          save_voltages = False, decibel_scale = False):

        def calc_power(f_bins, fft, f, delta_f):
                interval = (f_bins > f - delta_f) & (f_bins < f + delta_f)
                power = integrate.trapezoid(np.abs(fft[interval])**2, f_bins[interval])
                return power

        def calc_phase(f_bins, fft, f, delta_f):
                interval = (f_bins > f - delta_f) & (f_bins < f + delta_f)
                phases = np.angle(fft[interval])
                return np.angle(np.mean(np.exp(1j * phases))) if len(phases) else np.nan
        
        # Initialisation
        if scale == "linear":
            freqs = np.linspace(min_freq, max_freq, freq_amount)
        elif scale == "log":
            freqs = np.geomspace(min_freq, max_freq, freq_amount)
        else:
            raise ValueError(f"Invalid scale: '{scale}'. Use 'linear' or 'log'.")

        samples = int(fs*duration)
        t = np.arange(samples) / fs

        # Start of main loop for calculating the power
        # Generating voltages and sending it through circuit
        voltages_before = []
        voltages_after = []

        for freq in tqdm(freqs):
            sine = amplitude * np.sin(2 * np.pi * freq * t)
            initial_signal, post_signal = daq.write_and_read(sine)
            voltages_after.append(post_signal)
            voltages_before.append(initial_signal)
            if save_voltages:
                Functions.save_data_to_txt(post_signal, f"voltage_after_{freq:.2f}Hz")
                Functions.save_data_to_txt(initial_signal, f"voltage_before_{freq:.2f}Hz")

        # Taking the FFT of the voltages, both the initial and the sent-through-circuit
        # Decide whether to normalize the FFT in the arguments of the function
        ffts_before = []
        ffts_after = []

        for i in voltages_after:
            fft, fbins = Functions.fft(i, fs, normalize)
            ffts_after.append(fft)

        for i in voltages_before:
            fft, fbins = Functions.fft(i, fs, normalize)
            ffts_before.append(fft)

        # Calculating the power, both the initial and the sent-through-circuit
        powers_before = []
        powers_after = []

        for i, fft in enumerate(ffts_after):
            power = calc_power(fbins, fft, freqs[i], df)
            powers_after.append(power)

        for i, fft in enumerate(ffts_before):
            power = calc_power(fbins, fft, freqs[i], df)
            powers_before.append(power)

# Calculating the phase, both the initial and the sent-through-circuit
        phases_before = []
        phases_after = []

        for i, fft in enumerate(ffts_after):
            phase = calc_phase(fbins, fft, freqs[i], df)
            phases_after.append(phase)

        for i, fft in enumerate(ffts_before):
            phase = calc_phase(fbins, fft, freqs[i], df)
            phases_before.append(phase)

        # Calculating the magnitude transfer function values
        mag_transfer_function = np.sqrt(np.asarray(powers_after) / np.asarray(powers_before))
        if decibel_scale:
            mag_transfer_function = 20 * np.log10(mag_transfer_function)

        # Calculating the phase transfer function values
        phase_transfer_function = np.angle(np.exp(1j *(np.asarray(phases_after) - np.asarray(phases_before))))

        return mag_transfer_function, phase_transfer_function, freqs


    # Saves a list or array to a .txt file with a custom name.
    @staticmethod
    def save_data_to_txt(data, filename="data_output.txt", delimiter=","):
        array_to_save = np.asarray(data)
        np.savetxt(filename, array_to_save, delimiter=delimiter, fmt="%g")
        print(f"Successfully saved data to '{filename}'")
        

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
            FFT = np.fft.rfft(signal)
            frequencies = np.fft.rfftfreq(n, d=1 / fs)

            spectrum = np.abs(FFT)

            if n % 2 == 0:
                spectrum[1:-1] *= 2
            else:
                spectrum[1:] *= 2

            if normalize:
                spectrum = spectrum / n

            ax.plot(frequencies, spectrum)
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)

            if xlim is None:
                if scale == "semilogx" or scale == "loglog":
                    ax.set_xlim(frequencies[frequencies > 0].min(), fs / 2)
                else:
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
