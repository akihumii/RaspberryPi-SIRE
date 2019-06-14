from scipy import signal
from numba.decorators import jit


@jit
def filter_func(filter_flag, filter_z, filter_b, filter_a, data_buffer_all):
    if filter_flag:
        data_filtered, filter_z = signal.lfilter(filter_b, filter_a, data_buffer_all, zi=filter_z)
        return data_filtered, filter_z
    else:
        return data_buffer_all, filter_z


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
        self.nyq = 0
        self.high_pass_threshold = 0
        self.low_pass_threshold = 0

        self.set_filter_parameters(sampling_freq, hp_thresh, lp_thresh)
        self.set_filter()

    def set_filter(self):
        # self.filter_obj = signal.firwin(self.__num_taps,[self.low_pass_threshold, self.high_pass_threshold], pass_zero=False)
        self.set_filter_coeff()

        if self.filter_flag:
            self.filter_z = signal.lfilter_zi(self.filter_b, self.filter_a)

    def set_filter_coeff(self):
        self.filter_flag = True
        if self.high_pass_threshold > 0 and self.low_pass_threshold > 0:
            filter_thresholds = [self.high_pass_threshold, self.low_pass_threshold]
            filter_type = 'band'
        elif self.high_pass_threshold > 0 and self.low_pass_threshold == 0:
            filter_thresholds = self.high_pass_threshold
            filter_type = 'hp'
        elif self.high_pass_threshold == 0 and self.low_pass_threshold > 0:
            filter_thresholds = self.low_pass_threshold
            filter_type = 'low'
        else:
            self.filter_flag = False

        if self.filter_flag:
            [self.filter_b, self.filter_a] = signal.butter(
                self.__order, filter_thresholds, filter_type)

    def set_filter_parameters(self, sampling_freq, hp_thresh, lp_thresh):
        self.sampling_freq = sampling_freq
        self.nyq = 0.5 * self.sampling_freq
        self.high_pass_threshold = hp_thresh / self.nyq
        self.low_pass_threshold = lp_thresh / self.nyq

    def filter(self, data_buffer_all):
        # self.data_filtered = [[] for __ in range(len(data_buffer_all))]
        # for i, x in enumerate(data_buffer_all):
        #     self.data_filtered[i], self.filter_z = signal.lfilter(self.filter_obj, 1, [x], zi=self.filter_z)

        [self.data_filtered, self.filter_z] = filter_func(self.filter_flag, self.filter_z, self.filter_b, self.filter_a, data_buffer_all)
        return self.data_filtered

        # self.data_filtered = signal.lfilter(self.filter_obj, 1, data_buffer_all, zi=self.filter_z)

