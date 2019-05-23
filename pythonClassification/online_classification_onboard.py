import multiprocessing
import numpy as np
import time
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
BUFFER_SIZE_SENDING = 2  # buffer size to send data to socket
RINGBUFFER_SIZE = 40960
CHANNEL_LEN = 10
CHANNEL_DECODE = [4, 5, 6, 7]
PIN_LED = [[18, 4],
           [17, 27],
           [22, 5],
           [6, 13]]

FEATURES_ID = [5, 7]
PIN_STIM = 24  # HIGH to start sending command to stimulator
PIN_SM_CHANNEL = 25  # HIGH for multi-channel classification; LOW for single-channel classification
PIN_RESET = 12  # HIGH to reset the parameters and send the updated command to stimulator
PIN_SAVE = 16  # HIGH to stop saving; LOW to start a new csv file to save the counter and stimulation command
PIN_OFF = 21  # HIGH to close all ports and objects; LOW to start running the program again
PIN_CLOSED_LOOP = 19  # HIGH for single stimulation channel enable mode; LOW for close-loop step-size up-and-down mode
METHOD_IO = 'serial'  # METHOD for output display
METHOD_CLASSIFY = 'thresholds'  # input 'features' or 'thresholds'
# THRESHOLDS = np.genfromtxt('thresholds.txt', delimiter=',', defaultfmt='%f')

WINDOW_CLASS = 0.2  # second
WINDOW_OVERLAP = 0.05  # second
SAMPLING_FREQ = 1250  # sample/second

HP_THRESH = 100
LP_THRESH = 0
NOTCH_THRESH = 50

if __name__ == "__main__":
    pin_stim_obj = ConfigGPIO(PIN_STIM, 'in')
    pin_stim_obj.setup_GPIO()

    pin_sm_channel_obj = ConfigGPIO(PIN_SM_CHANNEL, 'in', pull_up_down='up')
    pin_sm_channel_obj.setup_GPIO()

    pin_reset_obj = ConfigGPIO(PIN_RESET, 'in', pull_up_down='up')
    pin_reset_obj.setup_GPIO()

    pin_save_obj = ConfigGPIO(PIN_SAVE, 'in', pull_up_down='up')
    pin_save_obj.setup_GPIO()

    pin_closed_loop_obj = ConfigGPIO(PIN_CLOSED_LOOP, 'in', pull_up_down='up')
    pin_closed_loop_obj.setup_GPIO()

    pin_off_obj = ConfigGPIO(PIN_OFF, 'in', pull_up_down='up')
    pin_off_obj.setup_GPIO()

    count = 1

    while True:
        if not pin_off_obj.input_GPIO():
            stop_event = multiprocessing.Event()  # to close all ports and objects in all threads
            stop_event.clear()

            raw_buffer_event = multiprocessing.Event()  # for the thread that send data to GUI
            raw_buffer_event.clear()

            change_parameter_event = multiprocessing.Event()  # change parameter when it receives signal from GUI
            change_parameter_event.clear()

            raw_buffer_queue = multiprocessing.Queue()  # saved the raw buffer to send to GUI
            change_parameter_queue = multiprocessing.Queue()  # to save the signal for parameter changing

            tcp_ip_sylph = TcpIp(IP_SYLPH, PORT_SYLPH, BUFFER_SIZE)  # create sylph socket object
            tcp_ip_odin = TcpIp(IP_ODIN, PORT_ODIN, BUFFER_SIZE_SENDING)  # create odin socket object
            tcp_ip_gui = TcpIp(IP_GUI, PORT_GUI, BUFFER_SIZE_SENDING)  # create gui socket object

            thread_bypass_data = BypassData(tcp_ip_gui, raw_buffer_event, raw_buffer_queue, change_parameter_queue, change_parameter_event, stop_event)  # send data to GUI in another thread
            thread_bypass_data.start()  # start thread to bypass data to GUI


            odin_obj = CommandOdin(tcp_ip_odin)  # create command odin object

            tcp_ip_sylph.connect()
            tcp_ip_odin.connect()

            ring_event = multiprocessing.Event()  # to stop the thread that process data
            ring_event.clear()

            ring_queue = multiprocessing.Queue()  # saved data across threads

            data_obj = DataHandler(CHANNEL_LEN, SAMPLING_FREQ, HP_THRESH, LP_THRESH, NOTCH_THRESH)  # create data class

            thread_process_classification = ProcessClassification(odin_obj, pin_sm_channel_obj, pin_reset_obj, pin_save_obj, pin_closed_loop_obj, METHOD_CLASSIFY, FEATURES_ID, METHOD_IO, PIN_LED, CHANNEL_LEN, WINDOW_CLASS, WINDOW_OVERLAP, SAMPLING_FREQ, ring_event, ring_queue, pin_stim_obj, change_parameter_queue, change_parameter_event, stop_event)  # thread 2: filter, extract features, classify
            thread_process_classification.start()  # start thread 2: online classification
            buffer_leftover = []

            while True:
                [buffer_read, buffer_raw] = tcp_ip_sylph.read(buffer_leftover)  # read buffer from socket
                if raw_buffer_event.is_set():  # will be true when there is a client successfully bound the server
                    raw_buffer_queue.put(buffer_raw)

                buffer_leftover, empty_buffer_flag = data_obj.get_buffer(buffer_read)  # get buffer into data

                if not empty_buffer_flag:
                    data_obj.get_data_channel()  # demultiplex and get the channel data
                    data_obj.fill_ring_data(ring_queue)  # fill the ring buffer for classification thread

                if pin_off_obj.input_GPIO():
                    stop_event.set()  # stop all the other threads

                    thread_bypass_data.join()
                    thread_process_classification.join()

                    tcp_ip_sylph.write_disconnect()
                    tcp_ip_odin.write_disconnect()

                    tcp_ip_gui.close()
                    tcp_ip_odin.close()
                    tcp_ip_sylph.close()

                    count = 1

                    time.sleep(1)  # wait for everyone to properly close

                    break

        else:
            print('transfer code sleeping... %d...' % count)
            time.sleep(1)
            count += 1

