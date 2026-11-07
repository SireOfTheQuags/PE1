import matplotlib.pyplot as plt
import numpy as np
from scipy import integrate
from tqdm.auto import tqdm
from scipy.optimize import curve_fit
import inspect


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
                          scale = "linear", man_freqs = None, normalize = True, 
                          save_voltages = False,
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
        if man_freqs is not None:
            freqs = np.concatenate((freqs, np.atleast_1d(man_freqs)))
        # Sort all frequencies from lowest to highest
        freqs = np.unique(freqs)

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
                    man_freqs = None, normalize=True,
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
        if man_freqs is not None:
            freqs = np.concatenate((freqs, np.atleast_1d(man_freqs)))
        # Sort all frequencies from lowest to highest
        freqs = np.unique(freqs)

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


    # Function to calculate a fit for the bode plots (for each plot this function must be called separately). 
    # 'Func' is a separately defined function of the theoretical model.
    # The first argument of 'func' must be the independent variable (frequency). 
    # Every argument after that represents a parameter that curve_fit is allowed to optimise.
    # Data is what we want the function to fit to. '**kwargs' are additional keyword you want to pass to 
    # curve_fit. DO NOT PASS THIS 'sigma'. PASS THE TOTAL ERRORS FOR THE RESPECTIVE VALUE AS VALUE FOR THE
    # "error" parameter: "mag total error" in linear terms for magnitude and "phase total error rad" for phase.
    # 'frequencies' must be positive, but do not need to be logarithmically spaced.
    # The fitted curve is evaluated on a logarithmically spaced frequency array.
    # If fitting phase, set 'unwrap_phase = True'
    @staticmethod
    def fit_bode_func(frequencies, func, ydata, ini_guess = None, 
                      unwrap_phase = False, error = None, **kwargs):
        kwargs.setdefault("absolute_sigma", True)

        frequencies = np.asarray(frequencies, dtype = float)
        ydata = np.asarray(ydata, dtype = float)

        if error is None:
            raise ValueError("Pass the total measurement errors via error=.")
        error = np.asarray(error, dtype=float)
        if error.shape != frequencies.shape or np.any(error <= 0):
            raise ValueError("error must match the frequency array and be strictly positive.")
        
        if frequencies.ndim != 1 or len(frequencies) < 2:
            raise ValueError("At least two frequencies are required.")
        if not np.all(np.isfinite(frequencies)) or np.any(frequencies <= 0):
            raise ValueError("Frequencies must be finite and positive.")
        if ydata.ndim != 1 or len(ydata) != len(frequencies):
            raise ValueError("ydata must match the frequency array.")
        if not np.all(np.isfinite(ydata)):
            raise ValueError("ydata must contain only finite values.")
        if np.any(np.diff(frequencies) <= 0):
            raise ValueError("Frequencies must be strictly ascending.")
        if unwrap_phase:
            ydata = np.unwrap(ydata)

        popt, pcov = curve_fit(func, frequencies, ydata, p0 = ini_guess, sigma = error, **kwargs)

        fit_freqs = np.logspace(np.log10(min(frequencies)), np.log10(max(frequencies)), 1000)
        fitted_data = func(fit_freqs, *popt)

        return fitted_data, fit_freqs, popt, pcov


    # Generate a bode plot and polar locus plot of the transfer function. 
    # Optionally plots the fit as well. The fit has to be passed as an argument separately.
    # Make sure the fit has the same dimensions as the data passed into this function.
    @staticmethod
    def bode_plot(frequencies, mean_magnitude, 
                  mean_phase, mag_total_error, 
                  phase_total_error_rad, 
                  fit_mag = None, fit_mag_func = None, fit_mag_popt = None, fit_mag_pcov = None,
                  fit_phase = None, fit_phase_func = None, fit_phase_popt = None, fit_phase_pcov = None,
                  fit_freqs = None):

        # Convert data to arrays
        frequencies = np.asarray(frequencies, dtype=float)
        mean_magnitude = np.asarray(mean_magnitude, dtype=float)
        mean_phase = np.asarray(mean_phase, dtype=float)
        mag_total_error = np.asarray(mag_total_error, dtype=float)
        phase_total_error_rad = np.asarray(phase_total_error_rad, dtype=float)

        # Validation for various things before plotting
        if not (len(frequencies) == len(mean_magnitude) == len(mean_phase) == len(mag_total_error) == len(phase_total_error_rad)):
            raise ValueError("All experimental arrays must have matching lengths.")
        if np.any(np.diff(frequencies) <= 0):
            raise ValueError("Frequencies must be strictly ascending.")
        if np.any(mean_magnitude <= 0):
            raise ValueError("Mean magnitudes must be positive.")
        if fit_mag is not None or fit_phase is not None:
            if fit_freqs is None:
                raise ValueError("fit_freqs must be provided when plotting fits.")
        if not np.all(np.isfinite(frequencies)) or np.any(frequencies <= 0):
            raise ValueError("Frequencies must be finite and positive.")
        if not all(np.all(np.isfinite(arr)) for arr in (mean_magnitude, mean_phase, mag_total_error, phase_total_error_rad)):
            raise ValueError("Experimental arrays must contain only finite values.")
        if np.any(mag_total_error < 0) or np.any(phase_total_error_rad < 0):
            raise ValueError("Uncertainties cannot be negative.")
        if fit_freqs is not None:
            fit_freqs = np.asarray(fit_freqs, dtype=float)
            if fit_freqs.ndim != 1 or not np.all(np.isfinite(fit_freqs)) or np.any(fit_freqs <= 0):
                raise ValueError("fit_freqs must be a finite, positive 1D array.")
        if fit_mag is not None:
            fit_mag = np.asarray(fit_mag, dtype=float)
            if fit_mag.shape != fit_freqs.shape:
                raise ValueError("fit_mag must match fit_freqs.")
        if fit_phase is not None:
            fit_phase = np.asarray(fit_phase, dtype=float)
            if fit_phase.shape != fit_freqs.shape:
                raise ValueError("fit_phase must match fit_freqs.")
        if fit_mag is not None:
            if not np.all(np.isfinite(fit_mag)) or np.any(fit_mag <= 0):
                raise ValueError("Fitted magnitudes must be finite and positive.")
        if fit_phase is not None:
            if not np.all(np.isfinite(fit_phase)):
                raise ValueError("Fitted phases must be finite.")
            
        if fit_mag is not None:
            if fit_mag_func is None or fit_mag_popt is None or fit_mag_pcov is None:
                raise ValueError("Magnitude fit function, parameters and covariance are required.")
            fit_mag_uncertainty = Functions.calculate_fit_uncertainty(fit_freqs, fit_mag_func, fit_mag_popt, fit_mag_pcov)

        if fit_phase is not None:
            if fit_phase_func is None or fit_phase_popt is None or fit_phase_pcov is None:
                raise ValueError("Phase fit function, parameters and covariance are required.")
            fit_phase_uncertainty = Functions.calculate_fit_uncertainty(fit_freqs, fit_phase_func, fit_phase_popt, fit_phase_pcov)

        # Magnitude error plot
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8))

        db_per_unit = 20 / np.log(10)
        magnitude_db = 20 * np.log10(mean_magnitude)
        mag_yerr_db = db_per_unit * mag_total_error / mean_magnitude

        # Plotting the magnitude fit
        if fit_mag is not None:
            fit_mag_db = 20 * np.log10(fit_mag)
            fit_mag_err_db = db_per_unit * fit_mag_uncertainty / fit_mag
            ax1.plot(fit_freqs, fit_mag_db, color='black', label='Magnitude fit')
            ax1.fill_between(fit_freqs, fit_mag_db - fit_mag_err_db, fit_mag_db + fit_mag_err_db,
                             color='black', alpha=0.15, label='Fit uncertainty')

        ax1.errorbar(frequencies, magnitude_db, yerr=mag_yerr_db, markersize = 2.5, fmt='o', capsize=3, ecolor = 'red', label='Experimental data')
        ax1.set_xscale('log')
        ax1.set_xlabel('Frequency (Hz)')
        ax1.set_ylabel('Magnitude (dB)')
        ax1.set_title('Experimental Transfer Function Magnitude')
        ax1.legend()
        ax1.grid(True, which='both')

        # Phase error plot
        mean_phase_unwrapped = np.unwrap(mean_phase)
        mean_phase_deg = np.degrees(mean_phase_unwrapped)
        phase_total_error_deg = np.degrees(phase_total_error_rad)

        # Plotting the phase fit 
        if fit_phase is not None:
            fit_phase_unwrapped = np.unwrap(fit_phase)
            inside = (frequencies >= fit_freqs[0]) & (frequencies <= fit_freqs[-1])
            i0 = np.argmax(inside)    # first data point that the fit curve actually covers
            fit_at_ref = np.interp(frequencies[i0], fit_freqs, fit_phase_unwrapped)
            fit_phase_unwrapped += 2 * np.pi * np.round((mean_phase_unwrapped[i0] - fit_at_ref) / (2 * np.pi))
            ax2.plot(fit_freqs, np.degrees(fit_phase_unwrapped), color='black', label='Phase fit')
            ax2.fill_between(fit_freqs, np.degrees(fit_phase_unwrapped - fit_phase_uncertainty), np.degrees(fit_phase_unwrapped + fit_phase_uncertainty), color='black', alpha=0.15, label='Fit uncertainty')

        ax2.errorbar(frequencies, mean_phase_deg, yerr=phase_total_error_deg, markersize = 2.5, fmt='o', capsize=3, ecolor = 'red', label = 'Experimental data')
        ax2.set_xscale('log')
        ax2.set_xlabel('Frequency (Hz)')
        ax2.set_ylabel('Phase (degrees)')
        ax2.set_title('Experimental Transfer Function Phase')
        ax2.legend()
        ax2.grid(True, which='both')

        plt.tight_layout()
        plt.show()

        # Polar plot
        fig, ax = plt.subplots(subplot_kw={"projection": "polar"}, figsize=(6, 6))
        ax.errorbar(mean_phase, mean_magnitude, yerr = mag_total_error, xerr = phase_total_error_rad, capsize = 1, markersize = 2.5, fmt='o', color="darkblue", lw=2, ecolor = 'red', label = 'Experimental data')
        ax.set_title("Polar Magnitude-Phase Locus", va="bottom")

        # Fitted polar curve
        if fit_mag is not None and fit_phase is not None:
            ax.plot(np.unwrap(fit_phase), fit_mag, color='black', label='Polar fit')

        ax.legend()
        plt.show()

        results = {}
        if fit_mag is not None:
            results["magnitude"] = Functions.report_fit("Magnitude", fit_mag_func, fit_mag_popt, fit_mag_pcov)
        if fit_phase is not None:
            results["phase"] = Functions.report_fit("Phase", fit_phase_func, fit_phase_popt, fit_phase_pcov)
        return results


    # Helper function meant solely for bode_plot function. Calculates uncertainties. Probably don't use standalone.
    @staticmethod
    def calculate_fit_uncertainty(fit_freqs, func, popt, pcov):

        popt = np.asarray(popt, dtype=float)
        pcov = np.asarray(pcov, dtype=float)
        fit_freqs = np.asarray(fit_freqs, dtype=float)

        if popt.ndim != 1 or len(popt) == 0:
            raise ValueError("popt must be a non-empty 1D array.")
        if pcov.shape != (len(popt), len(popt)):
            raise ValueError("Covariance matrix has an invalid shape.")
        if not np.all(np.isfinite(popt)) or not np.all(np.isfinite(pcov)):
            raise ValueError("Fit parameters and covariance must be finite.")

        jac = np.empty((len(fit_freqs), len(popt)))

        for j, p in enumerate(popt):
            h = 1e-6 * abs(p) if p != 0 else 1e-8
            p_plus, p_minus = popt.copy(), popt.copy()
            p_plus[j] += h
            p_minus[j] -= h
            jac[:, j] = (func(fit_freqs, *p_plus) - func(fit_freqs, *p_minus)) / (2 * h)

        if not np.all(np.isfinite(jac)):
            raise ValueError("Jacobian contains non-finite values; check the model function.")
        variance = np.einsum('ij,jk,ik->i', jac, pcov, jac)

        return np.sqrt(np.maximum(variance, 0.0))
    

    # Helper function meant solely for bode_plot function.
    # Prints and returns the fitted parameters with their standard errors (1 sigma).
    # Parameter names are taken from the model function's arguments (signature), excluding frequency.
    @staticmethod
    def report_fit(label, func, popt, pcov):
        popt = np.asarray(popt, dtype=float)
        perr = np.sqrt(np.diag(np.asarray(pcov, dtype=float)))
        names = list(inspect.signature(func).parameters)[1:]   # skip the frequency argument
        if len(names) != len(popt):
            names = [f"p{i}" for i in range(len(popt))]
        for name, value, err in zip(names, popt, perr):
            print(f"{label} fit: {name} = {value:.6g} ± {err:.2g}")
        return dict(zip(names, zip(popt, perr)))


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


