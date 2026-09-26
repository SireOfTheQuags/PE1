import numpy as np
from scipy.io.wavfile import write

fs = 44100

frequencies = [220, 262, 330, 392, 440]

signal = np.concatenate([
    np.sin(2 * np.pi * f * np.arange(fs) / fs)
    for f in frequencies
])

FFT = np.fft.fft(signal)

# Original
write("original.wav", fs, np.int16(signal * 32767))

# Keep magnitude, remove phase
magnitude_only = np.abs(FFT)
phase_removed = np.fft.ifft(magnitude_only).real

phase_removed /= np.max(np.abs(phase_removed))
write("phase_removed.wav", fs, np.int16(phase_removed * 32767))

# Keep phase, remove magnitude
phase_only = np.exp(1j * np.angle(FFT))
magnitude_removed = np.fft.ifft(phase_only).real

magnitude_removed /= np.max(np.abs(magnitude_removed))
write("magnitude_removed.wav", fs, np.int16(magnitude_removed * 32767))

original = signal

# Magnitude only
magnitude_only = np.abs(FFT)
signal_magnitude = np.fft.ifft(magnitude_only).real

# Phase only
phase_only = np.exp(1j * np.angle(FFT))
signal_phase = np.fft.ifft(phase_only).real

# Normalize all three to the same RMS
def normalize_rms(x):
    return x / np.sqrt(np.mean(x**2))

original = normalize_rms(original)
signal_magnitude = normalize_rms(signal_magnitude)
signal_phase = normalize_rms(signal_phase)

# Correlation with original
corr_magnitude = np.corrcoef(original, signal_magnitude)[0, 1]
corr_phase = np.corrcoef(original, signal_phase)[0, 1]

print("Magnitude correlation:", corr_magnitude)
print("Phase correlation:", corr_phase)