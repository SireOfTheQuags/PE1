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
                          duration, df, calibration_phase_offset, 
                          scale = "linear", normalize = True, 
                          save_voltages = False, decibel_scale = False,
                          initial_input_channel=None,
                          post_input_channel=None,
                          output_channel=None):

        def calc_power(f_bins, fft, f, delta_f):
            interval = (f_bins > f - delta_f) & (f_bins < f + delta_f)
            if np.count_nonzero(interval) < 2:
                raise ValueError(
                f"Fewer than two FFT bins found near {f:.2f} Hz. "
                "Increase df or duration."
                )
            power = integrate.trapezoid(np.abs(fft[interval])**2, f_bins[interval])
            return power

        def calc_phase(f_bins, fft, f, delta_f):
            if len(f_bins) == 0 or len(fft) == 0:
                return np.nan
            # FFT bin closest to desired frequency
            idx = np.argmin(np.abs(f_bins - f))
            # If closest bin is too far away just return nan
            if abs(f_bins[idx] - f) > delta_f:
                return np.nan
            return np.angle(fft[idx])

        channel_kwargs = {}
        if initial_input_channel is not None:
            channel_kwargs["initial_input_channel"] = initial_input_channel

        if post_input_channel is not None:
            channel_kwargs["post_input_channel"] = post_input_channel

        if output_channel is not None:
            channel_kwargs["output_channel"] = output_channel

            
        # Initialisation
        if scale == "linear":
            freqs = np.linspace(min_freq, max_freq, freq_amount)
        elif scale == "log":
            freqs = np.geomspace(min_freq, max_freq, freq_amount)
        else:
            raise ValueError(f"Invalid scale: '{scale}'. Use 'linear' or 'log'.")

        samples = int(fs * duration)
        t = np.arange(samples) / fs

        # Start of main loop for calculating the power
        # Generating voltages and sending it through circuit
        voltages_before = []
        voltages_after = []

        for freq in tqdm(freqs, desc="Creating and measuring signals"):
            sine = amplitude * np.sin(2 * np.pi * freq * t)
            initial_signal, post_signal = daq.write_and_read(sine, **channel_kwargs)
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
        powers_before = np.asarray(powers_before)
        powers_after = np.asarray(powers_after)
        if np.any(powers_before <= 0):
            raise ValueError("Input power is zero or negative at one or more frequencies.")
        
        mag_transfer_function = np.sqrt(powers_after / powers_before)
        if decibel_scale:
            mag_transfer_function = 20 * np.log10(mag_transfer_function)

        # Calculating the phase transfer function values
        calibration_phase_offset = np.asarray(calibration_phase_offset)
        if calibration_phase_offset.shape != freqs.shape:
            raise ValueError("Calibration offsets must match the measurement frequency array.")

        phase_transfer_function = np.angle(np.exp(1j * (
                                  np.asarray(phases_after)
                                  - np.asarray(phases_before) 
                                  - calibration_phase_offset
                                  )))

        return mag_transfer_function, phase_transfer_function, freqs


    # Measures the phase offset between two DAQ input channels at each frequency.
    # Both channels must measure the same signal, with the circuit bypassed.
    # Uses the same frequency settings (freq_amount, min_freq, max_freq, scale)
    # as calculate_power so that the calibration offsets match the measurement
    # frequencies and order. Also use the same fs, duration, df, and normalize
    # settings for consistent phase extraction. The DAQ sample rate must match fs.
    # Returns (phase_offsets, freqs), with phase offsets in radians, wrapped to
    # the range [-pi, pi]. For a single frequency, set min_freq = max_freq and
    # freq_amount = 1.
    @staticmethod
    def calc_phase_dif(daq, fs, freq_amount, min_freq, max_freq,
                    amplitude, duration, df, scale="linear",
                    normalize=True,
                    initial_input_channel=None,
                    post_input_channel=None,
                    output_channel=None):

        channel_kwargs = {}
        if initial_input_channel is not None:
            channel_kwargs["initial_input_channel"] = initial_input_channel

        if post_input_channel is not None:
            channel_kwargs["post_input_channel"] = post_input_channel

        if output_channel is not None:
            channel_kwargs["output_channel"] = output_channel


        # Generate the frequency array
        if scale == "linear":
            freqs = np.linspace(min_freq, max_freq, freq_amount)
        elif scale == "log":
            freqs = np.geomspace(min_freq, max_freq, freq_amount)
        else:
            raise ValueError(f"Invalid scale: '{scale}'. Use 'linear' or 'log'.")

        samples = int(fs * duration)
        t = np.arange(samples) / fs
        phase_offsets = []

        for freq in tqdm(freqs, desc="Calibrating phase"):
            sine = amplitude * np.sin(2 * np.pi * freq * t)

            # Measure the same signal on both input channels
            signal_before, signal_after = daq.write_and_read(sine, **channel_kwargs)

            # Calculate FFTs
            fft_before, f_bins = Functions.fft(signal_before, fs, normalize)
            fft_after, _ = Functions.fft(signal_after, fs, normalize)

            # Calculate each channel's phase
            idx = np.argmin(np.abs(f_bins - freq))
            if abs(f_bins[idx] - freq) > df:
                phase_offsets.append(np.nan)
                continue

            phase_before = np.angle(fft_before[idx])
            phase_after = np.angle(fft_after[idx])

            # Wrapped channel phase offset in radians
            phase_offset = np.angle(np.exp(1j * (phase_after - phase_before)))

            phase_offsets.append(phase_offset)

        return np.asarray(phase_offsets), freqs


    # Output is the propagated standard uncertainty (1 sigma) FOR THE THEORETICAL prediction of the curve,
    # in the units of func's output. This is meant solely to calculate the uncertainty caused by
    # the uncertainty in the values of the variables used. This gives a band around the theoretical curve. 
    # DO NOT add it to the error bars of the measured data points. Combine it with the experimental 
    # uncertainty only once, in the residual (data - theory).
    # cov: optional full covariance matrix (overrides independence assumption).
    @staticmethod
    def propagate_theo_error(func, inputs, cov=None):
        inputs = np.asarray(inputs, dtype=float)

        if inputs.ndim != 2 or inputs.shape[1] != 2:
            raise ValueError("Each input must be [value, uncertainty].")
        if not np.all(np.isfinite(inputs)):
            raise ValueError("Inputs must be finite.")
        
        values, sigmas = inputs[:, 0], inputs[:, 1]
        if np.any(sigmas < 0):
            raise ValueError("Uncertainties cannot be negative.")

        grad = np.empty(len(values))
        for i, v in enumerate(values):
            h = 1e-6 * abs(v) if v != 0 else (1e-6 * sigmas[i] or 1e-6)
            up, dn = values.copy(), values.copy()
            up[i] += h
            dn[i] -= h
            grad[i] = (func(*up) - func(*dn)) / (2 * h)

        if cov is None:
            return np.sqrt(np.sum((grad * sigmas) ** 2))
        return np.sqrt(grad @ np.asarray(cov) @ grad)


    # Saves a list or array to a .txt file with a custom name.
    @staticmethod
    def save_data_to_txt(data, filename="data_output.txt", delimiter=","):
        array_to_save = np.asarray(data)
        np.savetxt(filename, array_to_save, delimiter=delimiter, fmt="%g")
        print(f"Successfully saved data to '{filename}'")
        
    #
    @staticmethod
    def bode_plot(frequencies, mean_magnitude, 
                  mean_phase, mag_total_error, 
                  phase_total_error_rad):

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8))

        # Magnitude error plot
        magnitude_db = 20 * np.log10(mean_magnitude)
        magnitude_low = mean_magnitude - mag_total_error
        magnitude_high = mean_magnitude + mag_total_error
        magnitude_db_low = 20 * np.log10(magnitude_low)
        magnitude_db_high = 20 * np.log10(magnitude_high)
        mag_yerr_db = np.asarray([magnitude_db - magnitude_db_low, magnitude_db_high - magnitude_db])

        ax1.errorbar(frequencies, magnitude_db, yerr=mag_yerr_db, markersize = 2.5, fmt='o', capsize=3, ecolor = 'red')
        ax1.set_xscale('log')
        ax1.set_xlabel('Frequency (Hz)')
        ax1.set_ylabel('Magnitude (dB)')
        ax1.set_title('Experimental Transfer Function Magnitude')
        ax1.grid(True, which='both')

        # Phase error plot
        mean_phase_deg =np.degrees(mean_phase)
        phase_total_error_deg = np.degrees(phase_total_error_rad)

        ax2.errorbar(frequencies, mean_phase_deg, yerr=phase_total_error_deg, markersize = 2.5, fmt='o', capsize=3, ecolor = 'red')
        ax2.set_xscale('log')
        ax2.set_xlabel('Frequency (Hz)')
        ax2.set_ylabel('Phase (degrees)')
        ax2.set_title('Experimental Transfer Function Phase')
        ax2.grid(True, which='both')

        plt.tight_layout()
        plt.show()


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