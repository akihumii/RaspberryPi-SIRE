import numpy as np
from filtering import Filtering
from custom_filter import CustomFilter
from saving import Saving
from numba.decorators import jit


@jit
def get_data_channel_func(buffer_process, __sample_len, loc_start, __channel_len, __sync_pulse_len, __counter_len):
    data_all = [buffer_process[x: x + __sample_len - 1] for x in loc_start]
    data_all = np.vstack(data_all)  # stack the arrays into one column

    data_processed = data_all[:, 1:__sample_len - 1]  # exclude start flag and stop flag

    len_data = len(data_processed)

    [data_channel, data_rest] = np.hsplit(data_processed, [__channel_len * 2])
    [data_sync_pulse, data_counter] = np.hsplit(data_rest, [__sync_pulse_len])

    # convert two bytes into one 16-bit integer
    data_channel = np.ndarray(shape=(len_data, __channel_len), dtype='>u2',
                              buffer=data_channel.astype(np.uint8))
    data_counter = np.ndarray(shape=(len_data, __counter_len), dtype='>u2',
                              buffer=data_counter.astype(np.uint8))

    data_channel = np.roll(data_channel, -2)  # roll the data as the original matrix starts from channel 3

    data_channel = (data_channel.astype(np.float64) - 32768) * 0.000000195  # convert to volts

    data_raw = np.hstack([data_channel, data_sync_pulse, data_counter])

    # data_channel_filtered = np.transpose(np.vstack([filter_obj[x].filter(data_channel[:, x])
    #                                                 for x in range(__channel_len)]))
    #
    # data_processed = np.hstack([data_channel_filtered, data_sync_pulse, data_counter])

    return data_raw


@jit
def get_buffer_func(buffer_read, __flag_start_bit, __sample_len, __flag_end_bit, __flag_sync_pulse, __counter_len, buffer_process):
    loc_start_orig = np.argwhere(np.array(buffer_read) == __flag_start_bit)

    loc_start = [x[0] for x in loc_start_orig
                 if x + __sample_len < len(buffer_read)
                 and buffer_read[x + __sample_len - 1] == __flag_end_bit  # check end bit
                 and np.isin(buffer_read[x + __sample_len - (__counter_len * 2) - 2],
                             __flag_sync_pulse)  # check sync pulse
                 and buffer_read[x + __sample_len] == __flag_start_bit]  # check the next start bit

    if len(loc_start) > 0:
        [buffer_process, buffer_leftover] = np.split(buffer_read, [loc_start[-1] + __sample_len - 1])
        empty_buffer_flag = False
    else:
        buffer_leftover = buffer_read
        empty_buffer_flag = True

    return buffer_leftover, empty_buffer_flag, loc_start_orig, loc_start, buffer_process


class DataHandler(Saving):
    def __init__(self, channel_len, sampling_freq, hp_thresh, lp_thresh, notch_thresh):
        Saving.__init__(self)
        self.data_raw = []
        self.data_processed = []
        self.buffer_process = []
        self.loc_start = []
        self.loc_start_orig = []

        self.__flag_start_bit = 165
        self.__flag_end_bit = 90
        self.__flag_sync_pulse = [0, 255]
        self.__sample_len = 25
        self.__channel_len = channel_len
        self.__sync_pulse_len = 1
        self.__counter_len = 1
        self.__notch_bandwidth = 10
        self.__ring_column_len = self.__channel_len + self.__sync_pulse_len + self.__counter_len

        self.filter_obj = [CustomFilter(hp_thresh, lp_thresh, notch_thresh, self.__notch_bandwidth, sampling_freq) for __ in
                           range(self.__channel_len)]
        # self.filter_obj = [Filtering(sampling_freq, hp_thresh, lp_thresh, notch_thresh) for __ in range(self.__channel_len)]

    def get_buffer(self, buffer_read):
        [buffer_leftover, empty_buffer_flag, self.loc_start_orig, self.loc_start, self.buffer_process] = get_buffer_func(buffer_read, self.__flag_start_bit, self.__sample_len, self.__flag_end_bit, self.__flag_sync_pulse, self.__counter_len, self.buffer_process)

        return buffer_leftover, empty_buffer_flag

    def get_data_channel(self):  # obtain complete samples and form a matrix ( data_channel )
        self.data_raw = get_data_channel_func(self.buffer_process, self.__sample_len, self.loc_start, self.__channel_len, self.__sync_pulse_len, self.__counter_len)
        self.data_processed = np.transpose(np.vstack([self.filter_obj[x].filter_data(self.data_raw[:, x])
                                                      for x in range(self.__channel_len)]))
        self.data_processed = np.hstack([self.data_processed, self.data_raw[:, self.__channel_len:]])

    def fill_ring_data(self, ring_queue):
        if ring_queue.full():
            print("buffer full...")
        else:
            ring_queue.put_nowait(self.data_processed)



