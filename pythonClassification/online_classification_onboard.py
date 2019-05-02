import multiprocessing
import numpy as np
import RPi.GPIO as GPIO
from time import sleep
from tcpip import TcpIp
from data_handler import DataHandler
from process_classification import ProcessClassification
from command_odin import CommandOdin
from config_GPIO import ConfigGPIO
from bypass_data import BypassData
from saving import Saving

IP_SYLPH = "127.0.0.1"
IP_ODIN = "192.168.4.1"
IP_GUI = "192.168.4.3"
IP_STIMULATOR = ""
PORT_SYLPH = 8888
PORT_ODIN = 30000
PORT_GUI = 8000
PORT_STIMULATOR = 0

BUFFER_SIZE = 25 * 65  # about 50 ms
BUFFER_SIZE_SENDING = 1  # buffer size to send data to socket
RINGBUFFER_SIZE = 40960
CHANNEL_LEN = 10
CHANNEL_DECODE = [4, 5, 6, 7]
PIN_LED = [[18, 4],
           [17, 27],
           [22, 5],
           [6, 13]]

FEATURES_ID = [5, 7]
PIN_OFF = 24
METHOD_IO = 'GPIO'  # METHOD for output display
METHOD_CLASSIFY = 'thresholds'  # input 'features' or 'thresholds'
THRESHOLDS = [1, 1, 5e-3, 0]

WINDOW_CLASS = 0.2  # second
WINDOW_OVERLAP = 0.05  # second
SAMPLING_FREQ = 1250  # sample/second

HP_THRESH = 100
LP_THRESH = 0
NOTCH_THRESH = 50

if __name__ == "__main__":
    process_obj = ConfigGPIO(PIN_OFF, 'in')
    process_obj.setup_GPIO()

    count = 1
    count2 = 1

    raw_buffer_event = multiprocessing.Event()  # for the thread that send data to GUI
    raw_buffer_event.clear()

    raw_buffer_queue = multiprocessing.Queue()  # saved the raw buffer to send to GUI
    tcp_ip_gui = TcpIp(IP_GUI, PORT_GUI, BUFFER_SIZE_SENDING)  # create gui socket object

    thread_bypass_data = BypassData(tcp_ip_gui, raw_buffer_event, raw_buffer_queue)  # send data to GUI in another thread
    thread_bypass_data.start()  # start thread to bypass data to GUI

    tcp_ip_sylph = TcpIp(IP_SYLPH, PORT_SYLPH, BUFFER_SIZE)  # create sylph socket object
    tcp_ip_odin = TcpIp(IP_ODIN, PORT_ODIN, BUFFER_SIZE_SENDING)  # create odin socket object

    odin_obj = CommandOdin(tcp_ip_odin)  # create command odin object

    tcp_ip_sylph.connect()
    tcp_ip_odin.connect()

    ring_event = multiprocessing.Event()  # to stop the thread that process data
    ring_event.clear()

    ring_queue = multiprocessing.Queue()  # saved data across threads

    data_obj = DataHandler(CHANNEL_LEN, SAMPLING_FREQ, HP_THRESH, LP_THRESH, NOTCH_THRESH)  # create data class

    thread_process_classification = ProcessClassification(odin_obj, THRESHOLDS, METHOD_CLASSIFY, FEATURES_ID, METHOD_IO, PIN_LED, CHANNEL_LEN, WINDOW_CLASS, WINDOW_OVERLAP, SAMPLING_FREQ, ring_event, ring_queue, process_obj)  # thread 2: filter, extract features, classify
    thread_process_classification.start()  # start thread 2: online classification
    buffer_leftover = []

    saving_file_raw = Saving()

    while True:
        [buffer_read, buffer_raw] = tcp_ip_sylph.read(buffer_leftover)  # read buffer from socket
        if raw_buffer_event.is_set():  # will be true when there is a client successfully bound the server
            raw_buffer_queue.put(buffer_raw)

        buffer_leftover, empty_buffer_flag = data_obj.get_buffer(buffer_read)  # get buffer into data

        # saving_file_raw.save(data_obj.data_raw, "a")  # save the raw data

        if not empty_buffer_flag:
            data_obj.get_data_channel()  # demultiplex and get the channel data
            data_obj.fill_ring_data(ring_queue)  # fill the ring buffer for classification thread

