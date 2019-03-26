import multiprocessing
import RPi.GPIO as GPIO
from time import sleep
from tcpip import TcpIp
from data_handler import DataHandler
from process_classification import ProcessClassification
from command_odin import CommandOdin
from config_GPIO import ConfigGPIO

IP_SYLPH = "127.0.0.1"
IP_ODIN = "192.168.4.1"
IP_STIMULATOR = ""
PORT_SYLPH = 8888
PORT_ODIN = 30000
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
    while True:
        if process_obj.input_GPIO():
            # globals.initialize()  # initialize global variable ring data

            ring_lock = multiprocessing.Lock()
            ring_event = multiprocessing.Event()
            ring_event.set()

            ring_queue = multiprocessing.Queue()  # saved data across threads

            tcp_ip_sylph = TcpIp(IP_SYLPH, PORT_SYLPH, BUFFER_SIZE)  # create sylph socket object
            tcp_ip_odin = TcpIp(IP_ODIN, PORT_ODIN, BUFFER_SIZE)  # create odin socket object

            tcp_ip_sylph.connect()
            tcp_ip_odin.connect()

            data_obj = DataHandler(CHANNEL_LEN, SAMPLING_FREQ, HP_THRESH, LP_THRESH, NOTCH_THRESH)  # create data class

            odin_obj = CommandOdin(tcp_ip_odin)  # create command odin object

            thread_process_classification = ProcessClassification(odin_obj, FEATURES_ID, METHOD, PIN_LED, IP_STIMULATOR, PORT_STIMULATOR, CHANNEL_LEN, WINDOW_CLASS, WINDOW_OVERLAP, SAMPLING_FREQ, ring_event, ring_queue)  # thread 2: filter, extract features, classify

            thread_process_classification.start()  # start thread 2: online classification

            buffer_leftover = []  # run classification when classification GPIO is on

            tcp_ip_sylph.clear_buffer()  # clear socket buffer

            while process_obj.input_GPIO():
                buffer_read = tcp_ip_sylph.read(buffer_leftover)  # read buffer from socket
                buffer_leftover, empty_buffer_flag = data_obj.get_buffer(buffer_read)  # get buffer into data
                if not empty_buffer_flag:
                    data_obj.get_data_channel()  # demultiplex and get the channel data
                    # print(data_obj.data_processed[-1, -1])
                    # data_obj.save(data_obj.data_processed, "a")
                    data_obj.fill_ring_data(ring_queue)  # fill the ring buffer

            ring_event.clear()  # stop thread 2

            tcp_ip_sylph.write_disconnect()
            # tcp_ip_odin.write_disconnect()  # write 16 char to odin socket
            tcp_ip_sylph.close()
            tcp_ip_odin.close()

            thread_process_classification.join()  # terminate thread 2

            print('ring event cleared...')
        else:
            print('Main waiting for connection: %d...' % count)
            count += 1
            sleep(3)
