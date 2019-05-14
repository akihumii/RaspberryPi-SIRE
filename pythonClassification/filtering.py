import numpy as np
from scipy import signal
from numba import jitclass, float64, int8, boolean


spec = [
    ('data_filtered', float64[:]),
    ('sampling_freq', float64),
    ('notch_freq', float64),
    ('filter_flag', boolean),
    ('filter_z', float64[:]),
    ('filter_b', float64[:]),
    ('filter_a', float64[:]),
    ('order', int8),
    ('nyq', float64),
    ('high_pass_threshold', float64),
    ('low_pass_threshold', float64)
]


@jitclass(spec)
class Filtering(object):
    def __init__(self, sampling_freq, hp_thresh, lp_thresh, notch_thresh):
        self.data_filtered = np.zeros(0, dtype=np.float64)
        self.sampling_freq = sampling_freq

        # self.high_pass_threshold = 1. / hp_thresh
        # self.low_pass_threshold = 1. / lp_thresh
        self.notch_freq = notch_thresh
        self.filter_flag = True

        # self.filter_obj = None
        # self.filter_low_pass = None
        self.filter_z = np.zeros(0, dtype=np.float64)  # initial condition of the filter
        self.filter_b = np.zeros(0, dtype=np.float64)
        self.filter_a = np.zeros(0, dtype=np.float64)
        # self.z_low_pass = None
        # self.__num_taps = 150
        self.order = 5
        self.nyq = 0.5 * self.sampling_freq
        self.high_pass_threshold = hp_thresh / self.nyq
        self.low_pass_threshold = lp_thresh / self.nyq

        # self.set_filter()

    @property
    def set_filter(self):
        # self.filter_obj = signal.firwin(self.__num_taps,
        #                                 [self.low_pass_threshold, self.high_pass_threshold], pass_zero=False)

        if self.high_pass_threshold > 0 and self.low_pass_threshold > 0:
            filter_thresholds = [self.high_pass_threshold, self.low_pass_threshold]
            filter_type = 'band'
        elif self.high_pass_threshold > 0 and self.low_pass_threshold == 0:
            filter_thresholds = [self.high_pass_threshold]
            filter_type = 'hp'
        elif self.high_pass_threshold == 0 and self.low_pass_threshold > 0:
            filter_thresholds = [self.low_pass_threshold]
            filter_type = 'low'
        else:
            self.filter_flag = False

        if self.filter_flag:
            [self.filter_b, self.filter_a] = signal.butter(
                self.order, filter_thresholds, filter_type)

            self.filter_z = signal.lfilter_zi(self.filter_b, self.filter_a)
        return

    def filter(self, data_buffer_all):
        # self.data_filtered = [[] for __ in range(len(data_buffer_all))]
        # for i, x in enumerate(data_buffer_all):
        #     self.data_filtered[i], self.filter_z = signal.lfilter(self.filter_obj, 1, [x], zi=self.filter_z)

        if self.filter_flag:
            self.data_filtered, self.filter_z = signal.lfilter(self.filter_b, self.filter_a, data_buffer_all,
                                                               zi=self.filter_z)
            return self.data_filtered
        else:
            return data_buffer_all

        # self.data_filtered = signal.lfilter(self.filter_obj, 1, data_buffer_all, zi=self.filter_z)

