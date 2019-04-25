from numba.decorators import jit
import numpy as np


@jit
class Features:
    def __init__(self, data, sampling_freq, *args):
        self.data = data
        self.data_absolute = np.absolute(data)
        self.sampling_freq = sampling_freq
        self.run_list = args

    def extract_features(self):
        output = []
        if not self.run_list:  # if input arg is zero, run all.
            self.run_list = range(1, 9)

        if np.isin(1, self.run_list):
            output = np.append(output, self.get_min_value())
        if np.isin(2, self.run_list):
            output = np.append(output, self.get_max_value())
        if np.isin(3, self.run_list):
            output = np.append(output, self.get_mean_value())
        if np.isin(4, self.run_list):
            output = np.append(output, self.get_burst_len())
        if np.isin(5, self.run_list):
            output = np.append(output, self.get_area_under_curve())
        if np.isin(6, self.run_list):
            output = np.append(output, self.get_sum_diff())
        if np.isin(7, self.run_list):
            output = np.append(output, self.get_num_zero_crossing())
        if np.isin(8, self.run_list):
            output = np.append(output, self.get_num_sign_changes())

        return output

    def get_min_value(self):
        return np.min(self.data)

    def get_max_value(self):
        return np.max(self.data)

    def get_mean_value(self):
        return np.mean(self.data_absolute)

    def get_burst_len(self):
        return len(self.data) / self.sampling_freq

    def get_area_under_curve(self):
        return np.sum(self.data_absolute)

    def get_sum_diff(self):
        return np.sum(np.diff(self.data))

    def get_num_zero_crossing(self):
        return np.count_nonzero(np.diff(np.sign(self.data)))

    def get_num_sign_changes(self):
        return np.count_nonzero(np.diff(np.sign(np.diff(self.data))))


