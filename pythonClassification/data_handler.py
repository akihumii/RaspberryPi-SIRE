import numpy as np
from filtering import Filtering
from saving import Saving
from numba.decorators import jit


# @jit
# def get_data_channel_func(buffer_process, __sample_len, loc_start, __channel_len, __sync_pulse_len, __counter_len):
#     data_all = [buffer_process[x: x + __sample_len - 1] for x in loc_start]
#     data_all = np.vstack(data_all)  # stack the arrays into one column
#     data_processed = data_all[:, 1:__sample_len - 1]  # exclude start flag and stop flag
#     len_data = len(data_processed)
#     [data_channel, data_rest] = np.hsplit(data_processed, [__channel_len * 2])
#     [data_sync_pulse, data_counter] = np.hsplit(data_rest, [__sync_pulse_len])
#     # convert two bytes into one 16-bit integer
#     data_channel = np.ndarray(shape=(len_data, __channel_len), dtype='>u2',
#                               buffer=data_channel.astype(np.uint8))
#     data_counter = np.ndarray(shape=(len_data, __counter_len), dtype='>u2',
#                               buffer=data_counter.astype(np.uint8))
#     data_channel = np.roll(data_channel, -2)  # roll the data as the original matrix starts from channel 3
#     data_channel = (data_channel.astype(np.float64) - 32768) * 0.000000195  # convert to volts
#     data_raw = np.hstack([data_channel, data_sync_pulse, data_counter])
#     return data_raw


# @jit
# def get_buffer_func(buffer_read, __flag_start_bit, __sample_len, __flag_end_bit, __flag_sync_pulse, __counter_len, buffer_process):
#     loc_start_orig = np.argwhere(np.array(buffer_read) == __flag_start_bit)
#
#     loc_start = [x[0] for x in loc_start_orig
#                  if x + __sample_len < len(buffer_read)
#                  and buffer_read[x + __sample_len - 1] == __flag_end_bit  # check end bit
#                  and np.isin(buffer_read[x + __sample_len - (__counter_len * 2) - 2],
#                              __flag_sync_pulse)  # check sync pulse
#                  and buffer_read[x + __sample_len] == __flag_start_bit]  # check the next start bit
#
#     if len(loc_start) > 0:
#         [buffer_process, buffer_leftover] = np.split(buffer_read, [loc_start[-1] + __sample_len - 1])
#         empty_buffer_flag = False
#     else:
#         buffer_leftover = buffer_read
#         empty_buffer_flag = True
#
#     return buffer_leftover, empty_buffer_flag, loc_start_orig, loc_start, buffer_process


class DataHandler(Saving, Filtering):
    def __init__(self, param):
        Saving.__init__(self)
        Filtering.__init__(self, param.sampling_freq, param.hp_thresh, param.lp_thresh, param.notch_thresh)
        self.data_raw = []
        self.data_processed = []
        self.buffer_process = []
        self.loc_start = []
        self.loc_start_orig = []

        self.sampling_freq = param.sampling_freq
        self.hp_thresh = param.hp_thresh
        self.lp_thresh = param.lp_thresh
        self.notch_thresh = param.notch_thresh

        self.__flag_start_bit = 165
        self.__flag_end_bit = 90
        self.__flag_sync_pulse = [0, 255]
        self.__sample_len = 25
        self.__channel_len = param.channel_len
        self.__sync_pulse_len = 1
        self.__counter_len = 1
        self.__ring_column_len = self.__channel_len + self.__sync_pulse_len + self.__counter_len

        self.set_filter_obj()

    def get_buffer(self, buffer_read):
        self.loc_start_orig = np.argwhere(np.array(buffer_read) == self.__flag_start_bit)

        self.loc_start = [x[0] for x in self.loc_start_orig
                          if x + self.__sample_len < len(buffer_read)
                          and buffer_read[x + self.__sample_len - 1] == self.__flag_end_bit  # check end bit
                          and np.isin(buffer_read[x + self.__sample_len - (self.__counter_len * 2) - 2], self.__flag_sync_pulse)  # check sync pulse
                          and buffer_read[x + self.__sample_len] == self.__flag_start_bit]  # check the next start bit

        if len(self.loc_start) > 0:
            [self.buffer_process, buffer_leftover] = np.split(buffer_read, [self.loc_start[-1] + self.__sample_len - 1])
            empty_buffer_flag = False
        else:
            buffer_leftover = buffer_read
            empty_buffer_flag = True

        # code for compilation:
        # [buffer_leftover, empty_buffer_flag, self.loc_start_orig, self.loc_start, self.buffer_process] = get_buffer_func(buffer_read, self.__flag_start_bit, self.__sample_len, self.__flag_end_bit, self.__flag_sync_pulse, self.__counter_len, self.buffer_process)

        return buffer_leftover, empty_buffer_flag

    def get_data_channel(self):  # obtain complete samples and form a matrix ( data_channel )
        data_all = [self.buffer_process[x: x + self.__sample_len - 1] for x in self.loc_start]
        data_all = np.vstack(data_all)  # stack the arrays into one column
        self.data_processed = data_all[:, 1:self.__sample_len - 1]  # exclude start flag and stop flag
        len_data = len(self.data_processed)
        [data_channel, data_rest] = np.hsplit(self.data_processed, [self.__channel_len * 2])
        [data_sync_pulse, data_counter] = np.hsplit(data_rest, [self.__sync_pulse_len])
        # convert two bytes into one 16-bit integer
        data_channel = np.ndarray(shape=(len_data, self.__channel_len), dtype='>u2',
                                  buffer=data_channel.astype(np.uint8))
        data_counter = np.ndarray(shape=(len_data, self.__counter_len), dtype='>u2',
                                  buffer=data_counter.astype(np.uint8))
        data_channel = np.roll(data_channel, -2)  # roll the data as the original matrix starts from channel 3
        data_channel = (data_channel.astype(np.float64) - 32768) * 0.000000195  # convert to volts
        self.data_raw = np.hstack([data_channel, data_sync_pulse, data_counter])
        data_channel_filtered = np.transpose(np.vstack([self.filter_obj[x].filter(data_channel[:, x])
                                                        for x in range(self.__channel_len)]))
        self.data_processed = np.hstack([data_channel_filtered, data_sync_pulse, data_counter])

        # code for compilation:
        # self.data_raw = get_data_channel_func(self.buffer_process, self.__sample_len, self.loc_start, self.__channel_len, self.__sync_pulse_len, self.__counter_len)
        # self.data_processed = self.data_raw
        # self.data_processed = np.transpose(np.vstack([self.filter_obj[x].filter(self.data_raw[:, x])
        #                                               for x in range(self.__channel_len)]))
        # self.data_processed = np.hstack([self.data_processed, self.data_raw[:, self.__channel_len:]])

    def fill_ring_data(self, ring_queue):
        if ring_queue.full():
            print("buffer full...")
        else:
            ring_queue.put_nowait(self.data_processed)

    def set_filter_obj(self):
        self.filter_obj = [Filtering(self.sampling_freq, self.hp_thresh, self.lp_thresh, self.notch_thresh) for __ in range(self.__channel_len)]

    def update_filter_obj(self, data):
        address = {
            0xD6: self.update_sampling_freq,
            0xD7: self.update_hp_thresh,  # highpass cutoff freq
            0xD8: self.update_lp_thresh,  # lowpass cutoff freq
            0xD9: self.update_notch_thresh  # notch cutoff freq
        }
        address.get(data[0])(data[1])
        [self.filter_obj[i].set_filter_parameters(self.sampling_freq, self.hp_thresh, self.lp_thresh) for i in range(self.__channel_len)]
        [self.filter_obj[i].set_filter_coeff() for i in range(self.__channel_len)]

        print('updated filter...')

    def update_sampling_freq(self, data):
        print('updated sampling frequency for filtering...')
        print(data)
        self.sampling_freq = data

    def update_hp_thresh(self, data):
        print('updated highpass cutoff frequency...')
        print(data)
        self.hp_thresh = data

    def update_lp_thresh(self, data):
        print('updated lowpass cutoff frequency...')
        print(data)
        self.lp_thresh = data

    def update_notch_thresh(self, data):
        print('updated notch frequency...')
        print(data)
        self.notch_thresh = data




