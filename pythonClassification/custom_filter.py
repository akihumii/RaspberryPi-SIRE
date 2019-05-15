import numpy as np


class CustomFilter:
    def __init__(self, highpass_cutoff_freq, lowpass_cutoff_freq, notch_freq, notch_bandwidth, sampling_freq):
        self.notch_filter_enabled = False
        self.lowpass_filter_enabled = False
        self.highpass_filter_enabled = False
        self.highpass_cutoff_freq = highpass_cutoff_freq
        self.lowpass_cutoff_freq = lowpass_cutoff_freq
        self.notch_freq = notch_freq
        self.notch_bandwidth = notch_bandwidth
        self.sampling_freq = sampling_freq

        self.a0_hp = 0.
        self.a1_hp = 0.
        self.a2_hp = 0.
        self.b1_hp = 0.
        self.b2_hp = 0.
        self.a0_lp = 0.
        self.a1_lp = 0.
        self.a2_lp = 0.
        self.b1_lp = 0.
        self.b2_lp = 0.
        self.a0_n = 0.
        self.a1_n = 0.
        self.a2_n = 0.
        self.b1_n = 0.
        self.b2_n = 0.
        self.TWO_PI = 6.28318530718
        self.filtered_data = np.zeros(0, dtype=np.float64)
        self.filtered_data_hp = np.zeros(0, dtype=np.float64)
        self.filtered_data_n = np.zeros(0, dtype=np.float64)
        self.prev_raw_data = np.zeros(0, dtype=np.float64)

    def set_filter(self):
        if self.highpass_cutoff_freq:
            self.set_highpass_filter()

        if self.lowpass_cutoff_freq:
            self.set_lowpass_filter()

        if self.notch_freq:
            self.set_notch_filter()

    def set_lowpass_filter(self):
        fr = self.sampling_freq / self.lowpass_cutoff_freq
        omega = np.tan(np.pi / fr)
        c = 1 + np.cos(np.pi / 4) * omega + (omega * omega)
        self.a0_lp = (omega * omega) / c
        self.a2_lp = self.a0_lp
        self.a1_lp = self.a0_lp * 2
        self.b1_lp = 2 * (omega * omega - 1) / c
        self.b2_lp = (1 - np.cos(np.pi / 4) * omega + (omega * omega)) / c

        self.lowpass_filter_enabled = 1

    def set_notch_filter(self):
        self.notch_freq = self.notch_freq
        d = np.exp(-np.pi * self.notch_bandwidth / self.sampling_freq)

        # Calculate biquad IIR filter coefficients.
        self.b1_n = -(1.0 + d * d) * np.cos(2.0 * np.pi * self.notch_freq / self.sampling_freq)
        self.b2_n = d * d
        self.a0_n = (1 + d * d) / 2.0
        self.a1_n = self.b1_n
        self.a2_n = self.a0_n

        self.notch_filter_enabled = 1

    def set_highpass_filter(self):
        self.highpass_cutoff_freq = self.highpass_cutoff_freq
        self.highpass_cutoff_freq = 0.5 * self.sampling_freq - self.highpass_cutoff_freq
        fr = self.sampling_freq / self.highpass_cutoff_freq
        omega = np.tan(np.pi / fr)
        c = 1 + np.cos(np.pi / 4) * omega + (omega * omega)
        self.a0_hp = (omega * omega) / c
        self.a2_hp = self.a0_hp
        self.a1_hp = self.a0_hp * -2
        self.b1_hp = -2 * (omega * omega - 1) / c
        self.b2_hp = (1 - np.cos(np.pi / 4) * omega + (omega * omega)) / c

        self.highpass_filter_enabled = 1

    def filter_data(self, raw_data):
        if len(self.prev_raw_data >= 2):
            raw_data = np.append(self.prev_raw_data[:2], raw_data)

        prev_raw_data_temp = self.prev_raw_data
        self.prev_raw_data = raw_data[-2:]

        if self.notch_filter_enabled:
            raw_data = self.notch_filter(raw_data)

        if self.highpass_filter_enabled:
            raw_data = self.hipass_filter(raw_data)

        if self.lowpass_filter_enabled:
            raw_data = self.lopass_filter(raw_data)

        if len(prev_raw_data_temp >= 2):
            return raw_data[2:]
        else:
            return raw_data

    def hipass_filter(self, raw_data):
        if len(self.filtered_data_hp) > 1:
            self.filtered_data_hp = self.filtered_data_hp[-2:]
        else:
            self.filtered_data_hp = np.append(self.filtered_data_hp, raw_data[:2])

        for t in np.arange(2, len(raw_data)):
            temp = self.a0_hp * raw_data[t] + self.a1_hp * raw_data[t - 1] + self.a2_hp * raw_data[t - 2] - self.b1_hp * self.filtered_data_hp[t - 1] - self.b2_hp * self.filtered_data_hp[t - 2]
            self.filtered_data_hp = np.append(self.filtered_data_hp, temp)

        return self.filtered_data_hp
    
    def lopass_filter(self, raw_data):
        if len(self.filtered_data) > 1:
            self.filtered_data = self.filtered_data[-2:]
        else:
            self.filtered_data = np.append(self.filtered_data, raw_data[:2])

        for t in np.arange(2, len(raw_data)):
            temp = self.a0_lp * raw_data[t] + self.a1_lp * raw_data[t - 1] + self.a2_lp * raw_data[t - 2] - self.b1_lp * self.filtered_data[t - 1] - self.b2_lp * self.filtered_data[t - 2]
            self.filtered_data = np.append(self.filtered_data, temp)

        return self.filtered_data
    
    def notch_filter(self, raw_data):
        if len(self.filtered_data_n) > 1:
            self.filtered_data_n = self.filtered_data_n[-2:]
        else:
            self.filtered_data_n = np.append(self.filtered_data_n, raw_data[:2])

        for t in np.arange(2, len(raw_data)):
            temp = self.a0_n * raw_data[t] + self.a1_n * raw_data[t - 1] + self.a2_n * raw_data[t - 2] - self.b1_n * self.filtered_data_n[t - 1] - self.b2_n * self.filtered_data_n[t - 2]
            self.filtered_data_n = np.append(self.filtered_data_n, temp)

        return self.filtered_data_n




