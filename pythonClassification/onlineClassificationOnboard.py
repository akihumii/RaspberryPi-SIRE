import threading
import os
import datetime
import socket
import numpy as np
import pickle
import RPi.GPIO as GPIO
from numpy_ringbuffer import RingBuffer
from scipy import signal
from time import sleep


class Saving:  # save the data
    def __init__(self):
        now = datetime.datetime.now()
        self.__saving_dir_Date = "%d%02d%02d" % (now.year, now.month, now.day)
        self.__saving_filename = "data%s%02d%02d%02d%02d" % (
            self.__saving_dir_Date, now.hour, now.minute, now.second, now.microsecond)
        self.__saving_full_filename = os.path.join("Data", self.__saving_dir_Date, self.__saving_filename) + ".csv"

        self.__create_saving_dir()  # create saving directory, skip if the file exists

    def __create_saving_dir(self):
        if not os.path.exists(os.path.join("Data", self.__saving_dir_Date)):
            os.makedirs(os.path.join("Data", self.__saving_dir_Date))

    def save(self, data, *args):  # save the data
        saving_file_obj = open(self.__saving_full_filename, *args)
        np.savetxt(saving_file_obj, data, fmt="%f", delimiter=",")
        saving_file_obj.close()


class Filtering:
    def __init__(self, hp_thresh, lp_thresh, notch_thresh):
        self.data_filtered = []

        self.high_pass_threshold = 1. / hp_thresh
        self.low_pass_threshold = 1. / lp_thresh
        self.notch_freq = notch_thresh

        self.filter_obj = None
        self.filter_low_pass = None
        self.filter_z = None  # initial condition of the filter
        self.z_low_pass = None
        self.__num_taps = 150

        self.set_filter()

    def set_filter(self):
        self.filter_obj = signal.firwin(self.__num_taps,
                                        [self.low_pass_threshold, self.high_pass_threshold], pass_zero=False)
        self.filter_z = signal.lfilter_zi(self.filter_obj, 1)

    def filter(self, data_buffer_all):
        self.data_filtered = [signal.lfilter(self.filter_obj, 1, [x], zi=self.filter_z) for x in data_buffer_all]
        # self.data_filtered = signal.lfilter(self.filter_obj, 1, data_buffer_all, zi=self.filter_z)


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


class TcpIp:
    def __init__(self, ip_add, port, buffer_size):
        self.ip_add = ip_add
        self.port = port

        self.buffer_size = buffer_size
        self.socket_obj = None

        self.__connected = False

    def connect(self):  # connect to port
        self.socket_obj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        count = 1
        while not self.__connected:
            try:
                self.socket_obj.connect((self.ip_add, self.port))
                self.__connected = True
            except socket.error:
                self.__connected = False
                print("Connection failed... reconnecting %d time..." % count)
                count += 1
                sleep(2)

        print("Successfully connected...")

    def read(self, buffer_leftover):  # read data from port
        num_bytes_recorded = 0
        buffer_read = np.array([], dtype=np.uint8)
        while num_bytes_recorded < self.buffer_size:
            buffer_part = self.socket_obj.recv(self.buffer_size - num_bytes_recorded)
            if buffer_part == '':
                raise RuntimeError("socket connection broken")

            buffer_read = np.append(buffer_read, np.frombuffer(buffer_part, dtype=np.uint8))

            num_bytes_recorded = num_bytes_recorded + len(buffer_part)

        return np.append(buffer_leftover, buffer_read)


class Display:
    def __init__(self, channel_len):
        self.led_pin = 29
        GPIO.setmode(GPIO.BCM)  # Use "GPIO" pin numbering

        self.__setup()

    def test_blink(self):
        try:
            while True:
                GPIO.output(self.led_pin, GPIO.HIGH)
                sleep(1)
                GPIO.output(self.led_pin, GPIO.LOW)
                sleep(1)
        finally:
            GPIO.cleanup()

    def __setup(self):
        GPIO.setup(self.led_pin, GPIO.OUT)


class Demultiplex(Saving):
    def __init__(self, ringbuffer_size, channel_len, hp_thresh, lp_thresh, notch_thresh):
        global ring_data
        Saving.__init__(self)
        # Filtering.__init__(self, hp_thresh, lp_thresh, notch_thresh)
        self.data_orig = []
        self.data_processed = []
        self.buffer_process = []
        self.loc_start = []
        self.loc_start_orig = []

        self.__flag_start_bit = 165
        self.__flag_end_bit = 90
        self.__flag_counter = [0, 255]
        self.__sample_len = 25
        self.__channel_len = channel_len
        self.__sync_pulse_len = 1
        self.__counter_len = 1
        self.__ring_column_len = self.__channel_len + self.__sync_pulse_len + self.__counter_len

        ring_data = [RingBuffer(capacity=ringbuffer_size, dtype=np.float) for __ in range(self.__ring_column_len)]

    def get_buffer(self, buffer_read):
        self.loc_start_orig = np.argwhere(np.array(buffer_read) == self.__flag_start_bit)

        self.loc_start = [x[0] for x in self.loc_start_orig
                          if x + self.__sample_len < len(buffer_read)
                          and buffer_read[x + self.__sample_len - 1] == self.__flag_end_bit
                          and np.isin(buffer_read[x+self.__sample_len-(self.__counter_len*2)-2], self.__flag_counter)]

        [self.buffer_process, buffer_leftover] = np.split(buffer_read, [self.loc_start[-1]+self.__sample_len-1])

        return buffer_leftover

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

        self.data_processed = np.hstack([data_channel, data_sync_pulse, data_counter])

    def fill_ring_data(self, ring_lock):
        global ring_data
        # for x in range(self.__ring_column_len):
        #     for y in range(np.size(self.data_processed, axis=0)):
        #         ring_data[x].append(np.array(self.data_processed)[y, x])

        if (ring_data[0].maxlen - len(ring_data[0])) >= self.__sample_len:
            with ring_lock:  # lock the ring data while filling in
                for x in range(self.__ring_column_len):
                    ring_data[x].extend(np.array(self.data_processed)[:, x])
        else:
            print("buffer full...")

        # print("running thread for demultiplexing %d: " % len(ring_data[-1]))


class ProcessClassification(threading.Thread, Saving, Display):
    def __init__(self, channel_len, window_class, window_overlap, sampling_freq, ring_lock):
        global ring_data
        threading.Thread.__init__(self)
        Saving.__init__(self)

        self.clf = None
        self.window_class = window_class  # seconds
        self.window_overlap = window_overlap  # seconds
        self.sampling_freq = sampling_freq
        self.counter = -1
        self.ring_lock = ring_lock
        self.flag_channel_same_len = False

        self.__ring_channel_len = len(ring_data)
        self.__channel_len = channel_len

        self.data_raw = [RingBuffer(capacity=int(self.window_class * self.sampling_freq), dtype=np.float64)
                         for __ in range(self.__ring_channel_len)]

        self.channel_decode = []

        self.prediction = []
        # self.prediction = [[] for __ in range(self.__channel_len)]

        Display.__init__(self, self.__channel_len)

    def run(self):
        self.load_classifier()
        self.test_blink()
        while True:
            self.get_ring_data()
            # self.check_data_raw()
            self.classify()
            self.save(np.vstack(np.array(self.data_raw)).transpose(), "a")

    def get_ring_data(self):
        global ring_data
        while len(ring_data[0]) <= (self.window_overlap * self.sampling_freq):
            continue

        # when ring data has enough sample
        with self.ring_lock:
            for x in range(self.__ring_channel_len):
                self.data_raw[x].extend(np.array(ring_data[x]))  # fetch the data from ring buffer
                ring_data[x] = RingBuffer(capacity=ring_data[x].maxlen, dtype=np.float)  # clear the ring buffer

    def load_classifier(self):
        filename = sorted(x for x in os.listdir('classificationTmp') if x.startswith('classifier'))

        self.channel_decode = [x[x.find('Ch')+2] for x in filename]

        self.clf = [pickle.load(open(os.path.join('classificationTmp', x), 'rb')) for x in filename]

        self.prediction = [[] for __ in range(len(self.channel_decode))]
        print(len(self.prediction))

    def classify(self):
        for i, x in enumerate(self.channel_decode):
            feature_obj = Features(self.data_raw[int(x)-1], self.sampling_freq, [3, 7])
            features = feature_obj.extract_features()
            try:
                self.prediction[i] = self.clf[i].predict([features])
            except ValueError:
                print('prediction failed...')

        print('Prediction: %s', self.prediction)

    def check_data_raw(self):
        check_len = [len(self.data_raw[x]) for x in range(10)]

        # flag is true when raw data has data, when all the ring buffers have same length of data and when
        # counter has increased
        if len(self.data_raw[0]) > 0 and \
                all(x == check_len[0] for x in check_len) and \
                self.counter != self.data_raw[-1][-1]:
            # print("running thread for process classification")
            self.counter = self.data_raw[-1][-1]
            self.flag_channel_same_len = True
            print(check_len)
        else:
            self.flag_channel_same_len = False


class ReadNDemultiplex(threading.Thread):
    def __init__(self, tcp_ip_obj, data_obj, ring_lock):
        threading.Thread.__init__(self, target=ReadNDemultiplex)
        self.tcp_ip_obj = tcp_ip_obj
        self.data_obj = data_obj
        self.ring_lock = ring_lock

    def run(self):
        self.tcp_ip_obj.connect()
        buffer_leftover = []
        # ring_buffer = RingBuffer(capacity=40960, dtype=np.uint8)
        while True:
            global ring_data
            buffer_read = self.tcp_ip_obj.read(buffer_leftover)
            buffer_leftover = self.data_obj.get_buffer(buffer_read)
            self.data_obj.get_data_channel()  # demultiplex and get the channel data
            self.data_obj.save(self.data_obj.data_processed, "a")
            self.data_obj.fill_ring_data(self.ring_lock)  # fill the ring buffer


IP_ADD = "127.0.0.1"
PORT = 8888
BUFFER_SIZE = 25 * 65  # about 50 ms
RINGBUFFER_SIZE = 40960
CHANNEL_LEN = 10
CHANNEL_DECODE = [4, 5, 6, 7]

WINDOW_CLASS = 0.2  # second
WINDOW_OVERLAP = 0.05  # second
SAMPLING_FREQ = 1250  # sample/second

HP_THRESH = 50
LP_THRESH = 3500
NOTCH_THRESH = 50

if __name__ == "__main__":
    ring_lock = threading.Lock()

    tcp_ip_obj = TcpIp(IP_ADD, PORT, BUFFER_SIZE)  # create port object
    data_obj = Demultiplex(RINGBUFFER_SIZE, CHANNEL_LEN, HP_THRESH, LP_THRESH, NOTCH_THRESH)  # create data class

    thread_read_and_demultiplex = ReadNDemultiplex(tcp_ip_obj, data_obj, ring_lock)  # thread 1: reading buffer and demultiplex
    thread_process_classification = ProcessClassification(CHANNEL_LEN, WINDOW_CLASS, WINDOW_OVERLAP, SAMPLING_FREQ, ring_lock)  # thread 2: filter, extract features, classify

    thread_read_and_demultiplex.start()  # start thread 1
    thread_process_classification.start()  # start thread 2

    thread_read_and_demultiplex.join()  # join thread 1
    thread_process_classification.join()  # join thread 2

    # print("Finished...")
