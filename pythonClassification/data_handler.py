from numba.decorators import jit
import numpy as np
from filtering import Filtering
from saving import Saving


@jit
class DataHandler(Saving, Filtering):
    def __init__(self, channel_len, sampling_freq, hp_thresh, lp_thresh, notch_thresh):
        Saving.__init__(self)
        Filtering.__init__(self, sampling_freq, hp_thresh, lp_thresh, notch_thresh)
        self.data_orig = []
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
        self.__ring_column_len = self.__channel_len + self.__sync_pulse_len + self.__counter_len

        self.filter_obj = [Filtering(sampling_freq, hp_thresh, lp_thresh, notch_thresh) for __ in range(self.__channel_len)]

    def get_buffer(self, buffer_read):
        self.loc_start_orig = np.argwhere(np.array(buffer_read) == self.__flag_start_bit)

        self.loc_start = [x[0] for x in self.loc_start_orig
                          if x + self.__sample_len < len(buffer_read)
                          and buffer_read[x + self.__sample_len - 1] == self.__flag_end_bit  # check end bit
                          and np.isin(buffer_read[x+self.__sample_len-(self.__counter_len*2)-2], self.__flag_sync_pulse)  # check sync pulse
                          and buffer_read[x + self.__sample_len] == self.__flag_start_bit]  # check the next start bit

        if len(self.loc_start) > 0:
            [self.buffer_process, buffer_leftover] = np.split(buffer_read, [self.loc_start[-1]+self.__sample_len-1])
            empty_buffer_flag = False
        else:
            buffer_leftover = buffer_read
            empty_buffer_flag = True

        return buffer_leftover, empty_buffer_flag

    def get_data_channel(self):  # obtain complete samples and form a matrix ( data_channel )
        data_all = [self.buffer_process[x:x + self.__sample_len-1] for x in self.loc_start]
        data_all = np.vstack(data_all)  # stack the arrays into one column

        self.data_processed = data_all[:, 1:self.__sample_len-1]

        len_data = len(self.data_processed)

        [data_channel, data_rest] = np.hsplit(self.data_processed, [self.__channel_len*2])
        [data_sync_pulse, data_counter] = np.hsplit(data_rest, [self.__sync_pulse_len])

        data_channel = np.roll(data_channel, 2)  # roll the data as the original matrix starts from channel 3

        # convert two bytes into one 16-bit integer
        data_channel = np.ndarray(shape=(len_data, self.__channel_len), dtype='>u2',
                                  buffer=data_channel.astype(np.uint8))
        data_counter = np.ndarray(shape=(len_data, self.__counter_len), dtype='>u2',
                                  buffer=data_counter.astype(np.uint8))

        data_channel = (data_channel.astype(np.float64) - 32768) * 0.000195  # convert to integer

        data_channel = np.transpose(np.vstack([self.filter_obj[x].filter(data_channel[:, x])
                                               for x in range(self.__channel_len)]))

        self.data_processed = np.hstack([data_channel, data_sync_pulse, data_counter])

    def fill_ring_data(self, ring_queue):
        if ring_queue.full():
            print("buffer full...")
        else:
            ring_queue.put_nowait(self.data_processed)



