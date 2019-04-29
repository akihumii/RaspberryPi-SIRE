import multiprocessing
import numpy as np
import RPi.GPIO as GPIO
from time import sleep
from tcpip import TcpIp
from data_handler import DataHandler
from process_classification import ProcessClassification
from config_GPIO import ConfigGPIO
from bypass_data import BypassData

IP_SYLPH = "127.0.0.1"
IP_ODIN = "192.168.4.1"
IP_GUI = "192.168.4.3"
IP_STIMULATOR = ""
PORT_SYLPH = 8888
PORT_ODIN = 30000
PORT_GUI = 8000
PORT_STIMULATOR = 0

BUFFER_SIZE = 25 * 65  # about 50 ms
RINGBUFFER_SIZE = 40960
CHANNEL_LEN = 10
CHANNEL_DECODE = [4, 5, 6, 7]
PIN_LED = [[18, 4],
           [17, 27],
           [22, 5],
           [6, 13]]

FEATURES_ID = [5, 7]
PIN_OFF = 24
METHOD = 'GPIO'  # METHOD for output display

WINDOW_CLASS = 0.2  # second
WINDOW_OVERLAP = 0.05  # second
SAMPLING_FREQ = 1250  # sample/second

HP_THRESH = 0
LP_THRESH = 0
NOTCH_THRESH = 50

if __name__ == "__main__":
    process_obj = ConfigGPIO(PIN_OFF, 'in')
    process_obj.setup_GPIO()

    count = 1
    count2 = 1

    raw_buffer_event = multiprocessing.Event()  # for the thread that send data to GUI
    raw_buffer_event.clear()
    #
    raw_buffer_queue = multiprocessing.Queue()  # saved the raw buffer to send to GUI
    tcp_ip_gui = TcpIp(IP_GUI, PORT_GUI, 1)  # create gui socket object

    thread_bypass_data = BypassData(tcp_ip_gui, raw_buffer_event, raw_buffer_queue)  # send data to GUI in another thread
    thread_bypass_data.start()  # start thread to bypass data to GUI

    tcp_ip_sylph = TcpIp(IP_SYLPH, PORT_SYLPH, BUFFER_SIZE)  # create sylph socket object
    tcp_ip_odin = TcpIp(IP_ODIN, PORT_ODIN, BUFFER_SIZE)  # create odin socket object

    tcp_ip_sylph.connect()
    tcp_ip_odin.connect()

    ring_event = multiprocessing.Event()  # to stop the thread that process data
    # ring_event.set()
    ring_event.clear()
    #
    ring_queue = multiprocessing.Queue()  # saved data across threads

    data_obj = DataHandler(CHANNEL_LEN, SAMPLING_FREQ, HP_THRESH, LP_THRESH, NOTCH_THRESH)  # create data class

    thread_process_classification = ProcessClassification(FEATURES_ID, METHOD, PIN_LED, IP_STIMULATOR, PORT_STIMULATOR, CHANNEL_LEN, WINDOW_CLASS, WINDOW_OVERLAP, SAMPLING_FREQ, ring_event, ring_queue)  # thread 2: filter, extract features, classify
    thread_process_classification.start()  # start thread 2: online classification
    #
    # run classification when classification GPIO is on
    buffer_leftover = []

    while True:
        if process_obj.input_GPIO():
            if not ring_event.is_set():
                ring_event.set()  # start classifying
            # globals.initialize()  # initialize global variable ring data

            # clear socket buffer
            # tcp_ip_sylph.clear_buffer()
            # print('cleared buffer...')

            # while process_obj.input_GPIO():
            # print('inside the while loop to read buffer...')
            [buffer_read, buffer_raw] = tcp_ip_sylph.read(buffer_leftover)  # read buffer from socket
            # buffer_part = tcp_ip_sylph.read()  # read buffer from socket
            # buffer_read = np.append(buffer_leftover, np.frombuffer(buffer_part, dtype=np.uint8))  # attach the leftover to new data for local processing
            if raw_buffer_event.is_set():  # will be true when there is a client successfully bound the server
                # print('inserting buffer...')
                # buffer_sent = np.frombuffer(buffer_part, dtype=np.str)
                raw_buffer_queue.put_nowait(buffer_raw)
                # print(buffer_raw)
            # print(buffer_part)
            # else:
            # print('not inserting buffer...')
            # print(buffer_read)

            buffer_leftover, empty_buffer_flag = data_obj.get_buffer(buffer_read)  # get buffer into data
            if not empty_buffer_flag:
                data_obj.get_data_channel()  # demultiplex and get the channel data
                # print(data_obj.data_processed[-1, -1])
                # data_obj.save(data_obj.data_processed, "a")
                # print('putting data...')
                data_obj.fill_ring_data(ring_queue)  # fill the ring buffer for classification thread

            # ring_event.clear()
            # raw_buffer_event.clear()
            #
            # tcp_ip_sylph.write_disconnect()
            # # tcp_ip_odin.write_disconnect()  # write 16 char to odin socket
            # tcp_ip_sylph.close()
            # tcp_ip_odin.close()
            # tcp_ip_gui.close()

            # thread_process_classification.join()  # terminate thread 2
            # thread_bypass_data.join()  # terminate thread for bypassing data

            # print('ring event cleared...')
        else:
            if ring_event.is_set():
                ring_event.clear()

            [buffer_read, buffer_raw] = tcp_ip_sylph.read(buffer_leftover)  # read buffer from socket
            if raw_buffer_event.is_set():
                # print('inserting buffer...')
                # buffer_sent = np.frombuffer(buffer_part, dtype=np.str)
                raw_buffer_queue.put_nowait(buffer_raw)

            # print('Main waiting for connection: %d...' % count)
            # count += 1
            # sleep(3)
