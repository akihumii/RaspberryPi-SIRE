import numpy as np
import multiprocessing
import copy


class DynoHandler(multiprocessing.Process):
    def __init__(self, tcp_ip_dyno, dyno_queue, stop_event):
        multiprocessing.Process.__init__(self)
        self.tcp_ip_dyno = tcp_ip_dyno
        self.dyno_queue = dyno_queue
        self.stop_event = stop_event

    def run(self):
        print('started dyno handler thread...')
        # count = 1
        while True:
            client_socket = self.tcp_ip_dyno.create_host()
            # print('waiting for dyno client... %d...' % count)

            if client_socket:  # successfully connected
                client_socket_obj = copy.deepcopy(self.tcp_ip_dyno)
                client_socket_obj.socket_obj = client_socket
                client_socket_obj.socket_obj.setblocking(False)
                print('dyno client %s::%d successfully connected...' % (self.tcp_ip_dyno.ip_add, self.tcp_ip_dyno.port))

                while True:
                    dyno_data = client_socket_obj.read([], data_type='double')[0]
                    if len(dyno_data) > 0:
                        self.dyno_queue.put(dyno_data)
                        # print(dyno_data)

                        if int(dyno_data) == 99999:
                            break

                    if self.stop_event.is_set():
                        break

                client_socket_obj.close()
                count = 0

            # count += 1

            if self.stop_event.is_set():
                break

        print('thread to recevie dyno data has stopped...')
