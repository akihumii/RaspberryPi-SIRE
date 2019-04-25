from numba.decorators import jit
from scipy import signal


@jit
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
        self.filter_z = None  # initial condition of the filter
        self.filter_b = None
        self.filter_a = None
        self.z_low_pass = None
        self.__num_taps = 150
        self.__order = 5
        self.nyq = 0.5 * self.sampling_freq
        self.high_pass_threshold = hp_thresh / self.nyq
        self.low_pass_threshold = lp_thresh / self.nyq

        self.set_filter()

    def set_filter(self):
        # self.filter_obj = signal.firwin(self.__num_taps,
        #                                 [self.low_pass_threshold, self.high_pass_threshold], pass_zero=False)

        if self.high_pass_threshold > 0 and self.low_pass_threshold > 0:
            filter_thresholds = [self.high_pass_threshold, self.low_pass_threshold]
            filter_type = 'bandpass'
        elif self.high_pass_threshold > 0 and self.low_pass_threshold == 0:
            filter_thresholds = self.high_pass_threshold
            filter_type = 'highpass'
        elif self.high_pass_threshold == 0 and self.low_pass_threshold > 0:
            filter_thresholds = self.low_pass_threshold
            filter_type = 'lowpass'
        else:
            filter_thresholds = 0
            filter_type = 'highpass'
            self.filter_flag = False

        [self.filter_b, self.filter_a] = signal.butter(
            self.__order, filter_thresholds, btype=filter_type)

        self.filter_z = signal.lfilter_zi(self.filter_b, self.filter_a)

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

