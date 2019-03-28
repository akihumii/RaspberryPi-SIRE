from numba.decorators import jit
from filtering import Filtering
import numpy as np


# The original version is here: https://gist.github.com/ximeg/587011a65d05f067a29ce9c22894d1d2
# I made small changes and used numba to do it faster.

@jit
def moving_window_threhsolding(data, lag, threshold, influence):
    signals = np.zeros(len(data))
    filter_data = np.array(data)
    filter_avg = np.zeros(len(data))
    filter_std = np.zeros(len(data))
    filter_avg[lag - 1] = np.mean(data[0:lag])
    filter_std[lag - 1] = np.std(data[0:lag])
    for i in range(lag, len(data) - 1):
        if abs(data[i] - filter_avg[i - 1]) > threshold * filter_std[i - 1]:
            if data[i] > filter_avg[i - 1]:
                signals[i] = 1
            else:
                signals[i] = -1

            filter_data[i] = influence * data[i] + (1 - influence) * filter_data[i - 1]
            filter_avg[i] = np.mean(filter_data[(i - lag):i])
            filter_std[i] = np.std(filter_data[(i - lag):i])
        else:
            signals[i] = 0
            filter_data[i] = data[i]
            filter_avg[i] = np.mean(filter_data[(i - lag):i])
            filter_std[i] = np.std(filter_data[(i - lag):i])

    return dict(signals=np.asarray(signals),
                filter_avg=np.asarray(filter_avg),
                filter_std=np.asarray(filter_std))


def convert_TKEO(data, sampling_freq):
    filter_obj = Filtering(sampling_freq, 10, 500, 0)
    data = filter_obj.filter(data)

    filter_obj = Filtering(sampling_freq, 30, 300, 0)
    data = filter_obj.filter(data)

    [num_row, num_col] = np.shape(data)

    data_TKEO = [data[i, n]**2 - data[i+1, n]*data[i-1, n] for n in range(num_col) for i in range(1, num_row-1)]
    data_TKEO = np.vstack([data_TKEO[0, 0:], data_TKEO, data_TKEO[-1, 0:]])
    data_TKEO = np.abs(data_TKEO)

    filter_obj = Filtering(sampling_freq, 0, 50, 0)
    data_TKEO = filter_obj.filter(data_TKEO)

    return data_TKEO
