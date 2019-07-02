import multiprocessing
import copy


class ReceiveFilename(multiprocessing.Process):
    def __init__(self, tcp_ip_filename, stop_event, filename_queue):
        multiprocessing.Process.__init__(self)
        self.tcp_ip_filename = tcp_ip_filename
        self.stop_event = stop_event
        self.filename_queue = filename_queue

    def run(self):
        print('started socket server to receive filename...')
        # count = 1
        while True:
            client_socket = self.tcp_ip_filename.create_host()
            # print('Waiting for filename... %d...' % count)

            if client_socket:  # successfully connected
                client_socket_obj = copy.deepcopy(self.tcp_ip_filename)
                client_socket_obj.socket_obj = client_socket
                client_socket_obj.socket_obj.setblocking(False)
                print('filename client %s::%d successfully connected...' % (self.tcp_ip_filename.ip_add, self.tcp_ip_filename.port))

                while True:
                    filename = client_socket_obj.read([], data_type='text')[0][0]
                    if len(filename) > 0:
                        self.filename_queue.put(filename)
                        break

                    if self.stop_event.is_set():
                        break

                client_socket_obj.close()
                # count = 0

            # count += 1

            if self.stop_event.is_set():
                break

        print('thread to create server for receiving filename has stopped...')


