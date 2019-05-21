import numpy as np
from numba import jitclass, float64,int16 , int8, intp, boolean


spec = [
    ('notch_filter_enabled', boolean),
    ('lowpass_filter_enabled', boolean),
    ('highpass_filter_enabled', boolean),
    ('highpass_cutoff_freq', float64),
    ('lowpass_cutoff_freq', float64),
    ('notch_freq', float64),
    ('notch_bandwidth', int8),
    ('sampling_freq', int16),
    ('a0_hp', float64),
    ('a1_hp', float64),
    ('a2_hp', float64),
    ('b1_hp', float64),
    ('b2_hp', float64),
    ('a0_lp', float64),
    ('a1_lp', float64),
    ('a2_lp', float64),
    ('b1_lp', float64),
    ('b2_lp', float64),
    ('a0_n', float64),
    ('a1_n', float64),
    ('a2_n', float64),
    ('b1_n', float64),
    ('b2_n', float64),
    ('TWO_PI', float64),
    ('num_col', intp),
    ('filtered_data', float64[:, ::1]),
    ('filtered_data_hp', float64[:, :]),
    ('filtered_data_n', float64[:, :]),
    ('prev_raw_data', float64[:, :])
]


@jitclass(spec)
class CustomFilter(object):
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
        self.num_col = 10
        self.filtered_data = np.zeros((2, self.num_col), dtype=np.float64)
        self.filtered_data_hp = np.zeros((2, self.num_col), dtype=np.float64)
        self.filtered_data_n = np.zeros((2, self.num_col), dtype=np.float64)
        self.prev_raw_data = np.zeros((2, self.num_col), dtype=np.float64)

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

    def delete_rows(self, data, rows):
        # [num_row, num_col] = data.shape
        temp = np.ones(data.shape[0], dtype=np.intp)
        temp[:rows] = False
        return data[temp]

    def check_size(self, length_new):
        length_old = self.filtered_data.shape[0]
        if length_old < length_new:
            temp = np.zeros((length_old, self.num_col), dtype=float64)
            self.filtered_data = np.concatenate((self.filtered_data, temp))
            self.filtered_data_hp = np.concatenate((self.filtered_data_hp, temp))
            self.filtered_data_n = np.concatenate((self.filtered_data_n, temp))
            # self.filtered_data = np.array([list(self.filtered_data[i, :]) for i in range(length_old)] + [[0]*self.num_col])
            # self.filtered_data_hp = np.array([list(self.filtered_data_hp[i, :]) for i in range(length_old)] + [[0] * self.num_col])
            # self.filtered_data_n = np.array([list(self.filtered_data_n[i, :]) for i in range(length_old)] + [[0] * self.num_col])
        elif length_old > length_new:
            self.filtered_data = self.delete_rows(self.filtered_data, length_old - length_new)
            self.filtered_data_hp = self.delete_rows(self.filtered_data_hp, length_old - length_new)
            self.filtered_data_n = self.delete_rows(self.filtered_data_n, length_old - length_new)

    def filter_data(self, raw_data):
        length_new = raw_data.shape[0]
        self.check_size(length_new)  # check if the current size matches the raw data

        raw_data = raw_data.astype(np.float64)
        if not self.prev_raw_data[0,0]:
            raw_data = np.concatenate((self.prev_raw_data[:2, :], raw_data))
            # raw_data = np.array([list(self.prev_raw_data[i, :]) for i in range(2)] + [list(raw_data[i, :]) for i in range(length_new)], dtype=np.float64)

        prev_raw_data_temp = self.prev_raw_data[:2, :]
        self.prev_raw_data[:2, :] = raw_data[-2:, :]

        if self.notch_filter_enabled:
            raw_data = self.notch_filter(raw_data)

        if self.highpass_filter_enabled:
            raw_data = self.hipass_filter(raw_data)

        if self.lowpass_filter_enabled:
            raw_data = self.lopass_filter(raw_data)

        if not prev_raw_data_temp[0, 0]:
            return raw_data[2:, :]
        else:
            return raw_data

    def hipass_filter(self, raw_data):
        if not self.filtered_data_hp[0, 0]:
            self.filtered_data_hp[:2, :] = self.filtered_data_hp[-2:, :]
        else:
            self.filtered_data_hp[:2, :] = raw_data[:2, :]

        for t in np.arange(2, raw_data.shape[0]):
            temp = self.a0_hp * raw_data[t, :] + self.a1_hp * raw_data[t - 1, :] + self.a2_hp * raw_data[t - 2, :] - self.b1_hp * self.filtered_data_hp[t - 1, :] - self.b2_hp * self.filtered_data_hp[t - 2, :]
            self.filtered_data_hp[t, :] = temp

        return self.filtered_data_hp
    
    def lopass_filter(self, raw_data):
        if not self.filtered_data[0, 0]:
            self.filtered_data[:2, :] = self.filtered_data[-2:, :]
        else:
            self.filtered_data[:2, :] = raw_data[:2, :]

        for t in np.arange(2, raw_data.shape[0]):
            temp = self.a0_lp * raw_data[t, :] + self.a1_lp * raw_data[t - 1, :] + self.a2_lp * raw_data[t - 2, :] - self.b1_lp * self.filtered_data[t - 1, :] - self.b2_lp * self.filtered_data[t - 2, :]
            self.filtered_data[t, :] = temp

        return self.filtered_data
    
    def notch_filter(self, raw_data):
        if not self.filtered_data_n[0, 0]:
            self.filtered_data_n[:2, :] = self.filtered_data_n[-2:, :]
        else:
            self.filtered_data_n[:2, :] = raw_data[:2, :]

        for t in np.arange(2, raw_data.shape[0]):
            temp = self.a0_n * raw_data[t, :] + self.a1_n * raw_data[t - 1, :] + self.a2_n * raw_data[t - 2, :] - self.b1_n * self.filtered_data_n[t - 1, :] - self.b2_n * self.filtered_data_n[t - 2, :]
            self.filtered_data_n[t, :] = temp

        return self.filtered_data_n




