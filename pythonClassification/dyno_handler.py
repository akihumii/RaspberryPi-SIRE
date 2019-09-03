import numpy as np
import multiprocessing
import copy


class DynoHandler(multiprocessing.Process):
    def __init__(self, tcp_ip_dyno, dyno_queue, gui_client_event, stop_event, data_type):
        multiprocessing.Process.__init__(self)
        self.tcp_ip_dyno = tcp_ip_dyno
        self.dyno_queue = dyno_queue
        self.gui_client_event = gui_client_event
        self.stop_event = stop_event
        self.data_type = data_type

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
                    if not self.gui_client_event.is_set():
                        break

                    dyno_data = client_socket_obj.read([], data_type=self.data_type)[0]
                    if not np.any(np.isnan(dyno_data)) and len(dyno_data) > 0:
                        print(dyno_data)

                        if np.isin(99999, dyno_data):
                            self.dyno_queue.put(dyno_data[:-1])
                            break

                        self.dyno_queue.put(dyno_data)

                    if self.stop_event.is_set():
                        break

                client_socket_obj.close()
                self.gui_client_event.set()
                # count = 0

            # count += 1

            if self.stop_event.is_set():
                break

        print('thread to recevie dyno data %d has stopped...' % self.tcp_ip_dyno.port)
