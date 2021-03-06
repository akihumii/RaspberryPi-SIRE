from scipy import signal
from numba.decorators import jit
import numpy as np


# @jit
# def filter_func(filter_flag, filter_z, filter_b, filter_a, data_buffer_all):
#     if filter_flag:
#         data_filtered, filter_z = signal.lfilter(filter_b, filter_a, data_buffer_all, zi=filter_z)
#         return data_filtered, filter_z
#     else:
#         return data_buffer_all, filter_z


class Filtering:
    def __init__(self, sampling_freq, hp_thresh, lp_thresh, notch_thresh):
        self.data_filtered = []
        self.sampling_freq = sampling_freq

        # self.high_pass_threshold = 1. / hp_thresh
        # self.low_pass_threshold = 1. / lp_thresh
        self.notch_freq = notch_thresh
        self.filter_flag = True

        self.filter_obj = None
        self.filter_low_pass = None
        self.filter_z = None
        self.filter_z_5 = None  # initial condition of the highpass/lowpass filter
        self.filter_z_10 = None  # initial condition of the bandpass filter
        self.filter_b = None
        self.filter_a = None
        self.z_low_pass = None
        self.__num_taps = 150
        self.__order = 5
        self.nyq = 0
        self.high_pass_threshold = 0
        self.low_pass_threshold = 0

        self.initialize_filter()
        self.set_filter_parameters(sampling_freq, hp_thresh, lp_thresh)
        self.set_filter()

    def initialize_filter(self):
        [filter_b, filter_a] = signal.butter(5, 100./500, 'hp')
        self.filter_z_5 = signal.lfilter_zi(filter_b, filter_a)

        [filter_b, filter_a] = signal.butter(5, [100./500, 450./500], 'band')
        self.filter_z_10 = signal.lfilter_zi(filter_b, filter_a)

    def set_filter(self):
        # self.filter_obj = signal.firwin(self.__num_taps,[self.low_pass_threshold, self.high_pass_threshold], pass_zero=False)
        self.set_filter_coeff()

        if self.filter_flag:
            self.filter_z = signal.lfilter_zi(self.filter_b, self.filter_a)

    def set_filter_coeff(self):
        self.filter_flag = True
        filter_thresholds = 0
        if self.high_pass_threshold > 0 and self.low_pass_threshold > 0:
            filter_thresholds = np.array([self.high_pass_threshold, self.low_pass_threshold])
            filter_type = 'band'
            self.filter_flag = all(filter_thresholds > 0) and all(filter_thresholds < 1)
        elif self.high_pass_threshold > 0 and self.low_pass_threshold == 0:
            filter_thresholds = self.high_pass_threshold
            filter_type = 'hp'
            self.filter_flag = 0 < filter_thresholds < 1

        elif self.high_pass_threshold == 0 and self.low_pass_threshold > 0:
            filter_thresholds = self.low_pass_threshold
            filter_type = 'low'
            self.filter_flag = 0 < filter_thresholds < 1
        else:
            self.filter_flag = False

        if self.filter_flag:
            [self.filter_b, self.filter_a] = signal.butter(
                self.__order, filter_thresholds, filter_type)

        if self.filter_z is not None:
            filter_z = signal.lfilter_zi(self.filter_b, self.filter_a)
            if len(filter_z,) != len(self.filter_z):
                if len(filter_z) == 5:
                    self.filter_z_5 = filter_z
                    self.filter_z = self.filter_z_5
                elif len(filter_z) == 10:
                    self.filter_z_10 = filter_z
                    self.filter_z = self.filter_z_10

    def set_filter_parameters(self, sampling_freq, hp_thresh, lp_thresh):
        self.sampling_freq = sampling_freq
        self.nyq = 0.5 * self.sampling_freq
        self.high_pass_threshold = hp_thresh / self.nyq
        self.low_pass_threshold = lp_thresh / self.nyq

    def filter(self, data_buffer_all):
            if self.filter_flag:
                self.data_filtered, self.filter_z = signal.lfilter(self.filter_b, self.filter_a, data_buffer_all, zi=self.filter_z)
                return self.data_filtered
            else:
                return data_buffer_all

        # self.data_filtered = [[] for __ in range(len(data_buffer_all))]
        # for i, x in enumerate(data_buffer_all):
        #     self.data_filtered[i], self.filter_z = signal.lfilter(self.filter_obj, 1, [x], zi=self.filter_z)
        # self.data_filtered = signal.lfilter(self.filter_obj, 1, data_buffer_all, zi=self.filter_z)

        # code for compilation:
        # [self.data_filtered, self.filter_z] = filter_func(self.filter_flag, self.filter_z, self.filter_b, self.filter_a, data_buffer_all)
        # return self.data_filtered

