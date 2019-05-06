import numpy as np
import multiprocessing
import copy


class BypassData(multiprocessing.Process):
    def __init__(self, tcp_ip_obj, raw_buffer_event, raw_buffer_queue, stop_event):
        multiprocessing.Process.__init__(self)
        self.tcp_ip_obj = tcp_ip_obj
        self.raw_buffer_event = raw_buffer_event
        self.raw_buffer_queue = raw_buffer_queue
        self.stop_event = stop_event

    def run(self):
        print('started bypassing thread...')
        count = 1
        while True:
            client_socket = self.tcp_ip_obj.create_host()
            print('waiting for client... %d...' % count)

            if client_socket:  # successfully connected
                self.raw_buffer_event.set()  # to insert data into raw_buffer_queue
                client_socket_obj = copy.copy(self.tcp_ip_obj)
                client_socket_obj.socket_obj = client_socket
                print('accepted client...')

                broken_status = 0
                while not broken_status:  # stop sending when the pipe broke
                    if not self.raw_buffer_queue.empty():
                        data = self.raw_buffer_queue.get()
                        broken_status = client_socket_obj.send(data)

                    if self.stop_event.is_set():
                        break

                client_socket_obj.close()
                self.raw_buffer_event.clear()  # stop inserting buffer

                count = 0

            count += 1

            if self.stop_event.is_set():
                break

        print('data bypassing thread has stopped...')





