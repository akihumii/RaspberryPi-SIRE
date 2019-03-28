import numpy as np
from filtering import Filtering


class TKEO:
    def __init__(self, sampling_freq, point_start=35, point_end=100):
        self.sampling_freq = sampling_freq
        self.point_start = point_start
        self.point_end = point_end

    def convert_TKEO(self, data):
        filter_obj = Filtering(self.sampling_freq, 10, 500, 0)
        data = filter_obj.filter(data)

        filter_obj = Filtering(self.sampling_freq, 30, 300, 0)
        data = filter_obj.filter(data)

        [num_row, num_col] = np.shape(data)

        data_TKEO = [data[i, n]**2 - data[i+1, n]*data[i-1, n] for n in range(num_col) for i in range(1, num_row-1)]

        data_TKEO = np.vstack([data_TKEO[0, 0:], data_TKEO, data_TKEO[-1, 0:]])

        data_TKEO = np.abs(data_TKEO)

        filter_obj = Filtering(self.sampling_freq, 0, 50, 0)
        data_TKEO = filter_obj.filter(data_TKEO)

        return data_TKEO
