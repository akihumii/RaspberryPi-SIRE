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


def trigger(data, threshold, min_distance=0, point_start=0, multiple_peak=True):
    len_data = len(data)
    peaks = np.array([])
    locs = np.array([])
    for i in range(len_data-point_start):
        if all(data[i: i+point_start-1] > threshold):
            peaks = np.append(peaks, data[i])
            locs = np.append(locs, i)
            break

    if not peaks:
        return

    if multiple_peak:
        if i < len_data:
            for i in range(1, len_data-point_start):
                distance = i - peaks[-1]
                if all(data[i: i+point_start-1] > threshold) and distance > min_distance:
                    peaks = np.append(peaks, data[i])
                    locs = np.append(locs, i)

    return dict(peaks=peaks, locs=locs)


def find_trigger_end_point(data, threshold, locs_start, points):  # find end point when a number of points drop below a threshold after a starting point has been triggered
    peaks = np.array([])
    locs = np.array([])

    num_locs = len(locs_start)
    len_data = len(data)
    for i in range(num_locs):  # loop through all the starting points
        for j in range(locs_start[i], len_data-points):  # check until the end of data
            data_temp = data[j: j+points]
            if all(data_temp < threshold):
                peaks = np.append(peaks, data[j])
                locs = np.append(locs, j)
                break

    return dict(peaks=peaks, locs=locs)


def edit_burst_length(data_len, burst_len, locs_starting_point):
    locs_end_point = locs_starting_point + burst_len
    deleting_i = np.where(locs_end_point > data_len)
    locs_end_point = np.delete(locs_end_point, deleting_i)
    locs_starting_point = np.delete(locs_starting_point, deleting_i)

    return [locs_starting_point, locs_end_point]


def merge_channel_burst(locs_starting_point, locs_end_point):
    locs_starting_point_all = np.concatenate(locs_starting_point)
    locs_end_point_all = np.concatenate(locs_end_point)
    locs_all = np.vstack((locs_starting_point_all, locs_end_point_all))

    sorting_i = np.argsort(locs_all[0, :])  # sort the locations according to starting points
    locs_all = locs_all[:, sorting_i]

    target_i = np.diff(locs_all[1, :]) > 0  # omit the bursts that are included in the previous bursts
    target_i = np.append(True, target_i)
    locs_all = locs_all[target_i]

    # to omit the partially overlapping bursts
    overlap_bursts = np.vstack((np.append(locs_all[0, :], float("inf")), np.append(0, locs_all[1, :])))
    target_i = np.diff(overlap_bursts, 1, 1) < 0
    locs_all = locs_all[:, target_i]

    return [locs_all[0, :], locs_all[1, :]]


def trim_extra_burst_locs(locs_start, locs_end):
    locs_start_new = np.array([])

    if len(locs_start) != len(locs_end):
        locs_start = np.delete(locs_start, -1)

    locs_end_new = np.unique(locs_end)

    for x in locs_end_new:
        locs_start_new = np.append(locs_start_new, locs_start[np.argmax(locs_start > x)])

    if len(locs_start_new) != len(locs_end_new):
        locs_start_new = np.delete(locs_start_new, -1)




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
