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
from classification_decision import ClassificationDecision
from receive_filename import ReceiveFilename
from saving import Saving

PARAM = lambda: 0
PARAM.ip_sylph = "127.0.0.1"
PARAM.ip_odin = "192.168.4.1"
PARAM.ip_gui = "192.168.4.3"
PARAM.ip_stimulator = ""
PARAM.port_sylph = 8888
PARAM.port_odin = 30000
PARAM.port_filename = 7777
PARAM.port_gui = 8000
PARAM.port_stimulator = 0

PARAM.buffer_size = 25 * 65  # about 50 ms
PARAM.buffer_size_sending = 2  # buffer size to send data to socket
PARAM.buffer_filename = 1024
PARAM.ringbuffer_size = 40960
PARAM.channel_len = 10
PARAM.channel_decode = [4, 5, 6, 7]
PARAM.pin_led = [[18, 4],
                 [17, 27],
                 [22, 5],
                 [6, 13]]

PARAM.features_id = [5, 8]
PARAM.pin_stim = 24  # HIGH to start sending command to stimulator
PARAM.pin_sm_channel = 25  # HIGH for multi-channel classification; LOW for single-channel classification
PARAM.pin_reset = 12  # HIGH to reset the parameters and send the updated command to stimulator
PARAM.pin_save = 16  # HIGH to stop saving; LOW to start a new csv file to save the counter and stimulation command
PARAM.pin_off = 21  # HIGH to close all ports and objects; LOW to start running the program again
PARAM.pin_closed_loop = 19  # HIGH for single stimulation channel enable mode; LOW for close-loop step-size up-and-down mode
PARAM.pin_sh = 5  # HIGH for hardware control, LOW for software control
PARAM.pin_classify_method = 27  # HIGH for feature, LOW for thresholding classification
PARAM.method_io = 'serial'  # METHOD for output display
PARAM.method_classify = 'features'  # input 'features' or 'thresholds'
PARAM.robot_hand_output = '4F'  # input 'PSS' or '4F' or 'combo'
# THRESHOLDS = np.genfromtxt('thresholds.txt', delimiter=',', defaultfmt='%f')

PARAM.window_class = 0.2  # second
PARAM.window_overlap = 0.05  # second
PARAM.sampling_freq = 1250  # sample/second

PARAM.extend_stim = 0.2  # extend the stimulation for a time (seconds)

PARAM.hp_thresh = 100
PARAM.lp_thresh = 499
PARAM.notch_thresh = 50


def wave_signal(number, flag):
    if not count % 2:
        action_dic = {
            1: 2,
            2: 4,
            3: 2,
            4: 4,
            5: 0,
            6: 12,
            7: 14,
            8: 15
        }
        serial_obj.output_serial_direct(action_dic.get(number), 0)

        if not count % 180:
            flag = True

        if flag:
            if number >= 8:
                number = 1
                flag = False
            else:
                number += 1
        else:
            if number >= 7:
                number = 1
            else:
                number += 1

    return number, flag


def set_pins():
    pins_obj = lambda: 0
    pins_obj.pin_stim_obj = ConfigGPIO(PARAM.pin_stim, 'in')
    pins_obj.pin_stim_obj.setup_GPIO()

    pins_obj.pin_sm_channel_obj = ConfigGPIO(PARAM.pin_sm_channel, 'in', pull_up_down='up')
    pins_obj.pin_sm_channel_obj.setup_GPIO()

    pins_obj.pin_reset_obj = ConfigGPIO(PARAM.pin_reset, 'in', pull_up_down='up')
    pins_obj.pin_reset_obj.setup_GPIO()

    pins_obj.pin_save_obj = ConfigGPIO(PARAM.pin_save, 'in', pull_up_down='up')
    pins_obj.pin_save_obj.setup_GPIO()

    pins_obj.pin_closed_loop_obj = ConfigGPIO(PARAM.pin_closed_loop, 'in', pull_up_down='up')
    pins_obj.pin_closed_loop_obj.setup_GPIO()

    pins_obj.pin_off_obj = ConfigGPIO(PARAM.pin_off, 'in', pull_up_down='up')
    pins_obj.pin_off_obj.setup_GPIO()

    pins_obj.pin_sh_obj = ConfigGPIO(PARAM.pin_sh, 'in', pull_up_down='up')
    pins_obj.pin_sh_obj.setup_GPIO()

    pins_obj.pin_classify_method_obj = ConfigGPIO(PARAM.pin_classify_method, 'in', pull_up_down='up')
    pins_obj.pin_classify_method_obj.setup_GPIO()

    return pins_obj


if __name__ == "__main__":
    pins_obj = set_pins()

    count = 1

    serial_obj = ClassificationDecision(PARAM.method_io, PARAM.pin_led, 'out', PARAM.robot_hand_output)
    serial_obj.setup()

    current_sign = 1
    hidden_flag = False

    while True:
        if not pins_obj.pin_off_obj.input_GPIO():
            stop_event = multiprocessing.Event()  # to close all ports and objects in all threads
            stop_event.clear()

            raw_buffer_event = multiprocessing.Event()  # for the thread that send data to GUI
            raw_buffer_event.clear()

            change_parameter_event = multiprocessing.Event()  # change parameter when it receives signal from GUI
            change_parameter_event.clear()

            raw_buffer_queue = multiprocessing.Queue()  # saved the raw buffer to send to GUI
            change_parameter_queue = multiprocessing.Queue()  # to save the signal for parameter changing
            filter_parameters_queue = multiprocessing.Queue()  # for thread_bypass_data to store filtering parameters for dataHandler to use
            filename_queue = multiprocessing.Queue()  # for storing filename

            tcp_ip_sylph = TcpIp(PARAM.ip_sylph, PARAM.port_sylph, PARAM.buffer_size)  # create sylph socket object
            tcp_ip_odin = TcpIp(PARAM.ip_odin, PARAM.port_odin, PARAM.buffer_size_sending)  # create odin socket object
            tcp_ip_gui = TcpIp(PARAM.ip_gui, PARAM.port_gui, PARAM.buffer_size_sending)  # create gui socket object
            tcp_ip_filename = TcpIp(PARAM.ip_gui, PARAM.port_filename, PARAM.buffer_filename)  # create socket to receive filename

            thread_bypass_data = BypassData(tcp_ip_gui, raw_buffer_event, raw_buffer_queue, change_parameter_queue, change_parameter_event, filter_parameters_queue, stop_event)  # send data to GUI in another thread
            thread_bypass_data.start()  # start thread to bypass data to GUI

            odin_obj = CommandOdin(tcp_ip_odin)  # create command odin object

            tcp_ip_sylph.connect()
            tcp_ip_odin.connect()

            ring_event = multiprocessing.Event()  # to stop the thread that process data
            ring_event.clear()

            ring_queue = multiprocessing.Queue()  # saved data across threads

            data_obj = DataHandler(PARAM)  # create data class

            thread_process_classification = ProcessClassification(odin_obj, pins_obj, PARAM, ring_event, ring_queue, change_parameter_queue, change_parameter_event, stop_event, filename_queue)  # thread 2: filter, extract features, classify
            thread_process_classification.start()  # start thread 2: online classification
            buffer_leftover = []

            thread_receive_filename = ReceiveFilename(tcp_ip_filename, stop_event, filename_queue)
            thread_receive_filename.start()

            # saving_obj = Saving()

            while True:
                [buffer_read, buffer_raw] = tcp_ip_sylph.read(buffer_leftover)  # read buffer from socket
                if raw_buffer_event.is_set():  # will be true when there is a client successfully bound the server
                    raw_buffer_queue.put(buffer_raw)

                buffer_leftover, empty_buffer_flag = data_obj.get_buffer(buffer_read)  # get buffer into data

                if not empty_buffer_flag:
                    if not filter_parameters_queue.empty():
                        data_obj.update_filter_obj(filter_parameters_queue.get())
                    data_obj.get_data_channel()  # demultiplex and get the channel data
                    data_obj.fill_ring_data(ring_queue)  # fill the ring buffer for classification thread
                    # saving_obj.save(data_obj.data_raw, "a")

                if pins_obj.pin_off_obj.input_GPIO():
                    stop_event.set()  # stop all the other threads

                    thread_bypass_data.join()
                    thread_process_classification.join()
                    thread_receive_filename.join()

                    tcp_ip_sylph.write_disconnect()
                    tcp_ip_odin.write_disconnect()

                    tcp_ip_gui.close()
                    tcp_ip_filename.close()
                    tcp_ip_odin.close()
                    tcp_ip_sylph.close()

                    count = 1

                    time.sleep(1)  # wait for everyone to properly close

                    break

        else:
            print('transfer code sleeping... %d...' % count)
            [current_sign, hidden_flag] = wave_signal(current_sign, hidden_flag)
            time.sleep(1)
            count += 1

