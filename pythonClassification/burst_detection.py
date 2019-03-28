from numba.decorators import jit
from filtering import Filtering
import numpy as np
import matplotlib.pyplot as plt


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

    signals = np.asarray(signals)
    filter_avg = np.asarray(filter_avg)
    filter_std = np.asarray(filter_std)

    baseline_loc = [not x for x in signals]
    baseline = data[baseline_loc]
    baseline_std = np.std(baseline)

    return dict(signals=signals,
                filter_avg=filter_avg,
                filter_std=filter_std,
                baseline=baseline,
                baseline_std=baseline_std)


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


def trigger(data, threshold, min_distance=0, point_start=0, point_end=0, multiple_peak=True):
    len_data = len(data)
    peaks = np.array([])
    locs = np.array([])
    for i in range(len_data-point_start):
        if data[i: i+point_start-1] > threshold:
            peaks = np.append(peaks, data[i])
            locs = np.append(locs, i)
            break

    if not peaks:
        return

    if multiple_peak:
        if i < len_data:
            for i in range(1, len_data-point_start):
                distance = i - peaks[-1]
                if data[i: i+point_start-1] > threshold and distance > min_distance:
                    peaks = np.append(peaks, data[i])
                    locs = np.append(locs, i)



def visualize_baseline(data1, data2):
    plt.figure()
    ax1 = plt.subplot(121)
    plt.grid(True)
    plt.plot(data1)
    ax2 = plt.subplot(122, sharey=ax1)
    plt.grid(True)
    plt.title('1250, 2.5, 0')
    plt.plot(data2)


def analyse_data():
    data_all = np.genfromtxt('data_20190123_110730.csv', delimiter=',')
    data = data_all[0:, 5]
    obj_filter = Filtering(1250, 50, 0, 0, persistent_memory=False)
    data_filter = obj_filter.filter(data)

    result = moving_window_threhsolding(data_filter, 1000, 2.5, 0)
    baseline = result.get('baseline')

    visualize_baseline(data_filter, baseline)

    print('Finished...')
