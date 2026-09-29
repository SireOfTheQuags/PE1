from mydaq import MyDAQ
import numpy as np
import matplotlib.pyplot as plt

fs = 100000

daq = MyDAQ()

daq.set_sample_rate(fs)



data = daq.record_voltage(10)
data = np.asarray(data)


n=20
data=n*data

data[data > 10] = 0
data[data < -10] = 0

print(np.max(data))

print(data[25:])

daq.generate_signal(data)


FFT=np.fft.fft(data)

FFT_MAGNORM = FFT/np.abs(FFT)

FFT_inv = np.fft.ifft(FFT_MAGNORM)

daq.generate_signal(40*FFT_inv)


FFT_PHASENORM = FFT * np.exp(1j*(-np.angle(FFT)))
FFT_inv = np.fft.ifft(FFT_PHASENORM)
daq.generate_signal(FFT_inv/100)


FFT = FFT[:len(FFT)//2]/len(data)



k = np.arange(0, len(data))
fk = k*fs/len(data)
fk = fk[:len(fk)//2]



plt.plot(fk, np.abs(FFT))
plt.xscale("log")
# plt.xlim(0,500)
plt.xlabel("Frequency (Hz)")
plt.ylabel("Amplitude (V)")










