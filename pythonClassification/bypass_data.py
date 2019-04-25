import numpy as np
import multiprocessing
import copy


class BypassData(multiprocessing.Process):
    def __init__(self, tcp_ip_obj, raw_buffer_event, raw_buffer_queue):
        multiprocessing.Process.__init__(self)
        # self.ring_event = ring_event
        self.tcp_ip_obj = tcp_ip_obj
        # self.raw_buffer_event = raw_buffer_event
        self.raw_buffer_event = raw_buffer_event
        self.raw_buffer_queue = raw_buffer_queue

    def run(self):
        print('started bypassing thread...')
        count = 1
        while True:
        # while self.ring_event.is_set() and self.raw_buffer_thread_event.is_set():
            client_socket = self.tcp_ip_obj.create_host()
            print('waiting for client... %d...' % count)

            if client_socket:  # successfully connected
                self.raw_buffer_event.set()  # to insert data into raw_buffer_queue
                client_socket_obj = copy.copy(self.tcp_ip_obj)
                client_socket_obj.socket_obj = client_socket
                print('accepted client...')

                # while True:
                    # while self.ring_event.is_set() and not self.tcp_ip_obj.read():  # keep looping until receiving something in socket
                    # if not self.ring_event.is_set():  # keep looping until receiving something in socket
                    #     break
                broken_status = 0
                while not broken_status:  # stop sending when the pipe broke
                    if not self.raw_buffer_queue.empty():
                        data = self.raw_buffer_queue.get_nowait()
                        broken_status = client_socket_obj.send(data)
            #     print('successfully send data to GUI...')
            # else:
            #     print('no data in buffer...')

                client_socket_obj.close()
                self.raw_buffer_event.clear()  # stop inserting buffer

                count = 0

            count += 1
            # print('stopped bypassing thread...')





