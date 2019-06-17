import numpy as np
import multiprocessing
import copy


class BypassData(multiprocessing.Process):
    def __init__(self, tcp_ip_obj, raw_buffer_event, raw_buffer_queue, change_parameter_queue, change_parameter_event, filter_parameters_queue, stop_event):
        multiprocessing.Process.__init__(self)
        self.tcp_ip_obj = tcp_ip_obj
        self.raw_buffer_event = raw_buffer_event
        self.raw_buffer_queue = raw_buffer_queue
        self.filter_parameters_queue = filter_parameters_queue
        self.change_parameter_queue = change_parameter_queue
        self.change_parameter_event = change_parameter_event
        self.stop_event = stop_event
        self.classification_param_byte_len = 3

        self.address = {
            0xD6: True,  # sampling freq
            0xD7: True,  # highpass cutoff freq
            0xD8: True,  # lowpass cutoff freq
            0xD9: True  # notch cutoff freq
        }

        self.address_2bytes = {
            0xD6: True,  # sampling freq
            0xD7: True,  # highpass cutoff freq
            0xD8: True,  # lowpass cutoff freq
            0xD9: True,  # notch cutoff freq
            0xDA: True
        }

        self.address_sampling_frequency = 0xD6

    def run(self):
        print('started bypassing thread...')
        count = 1
        while True:
            client_socket = self.tcp_ip_obj.create_host()
            print('waiting for client... %d...' % count)

            if client_socket:  # successfully connected
                self.raw_buffer_event.set()  # to insert data into raw_buffer_queue
                client_socket_obj = copy.deepcopy(self.tcp_ip_obj)
                client_socket_obj.socket_obj = client_socket
                client_socket_obj.buffer_size = self.classification_param_byte_len
                client_socket_obj.socket_obj.setblocking(False)

                print('accepted client...')

                broken_status = 0
                while not broken_status:  # stop sending when the pipe broke
                    if not self.raw_buffer_queue.empty():  # send data to client
                        data = self.raw_buffer_queue.get()
                        broken_status = client_socket_obj.send(data)

                    # print('reading from client socket...')
                    data_recv = client_socket_obj.read([])[0]
                    if len(data_recv) > 0:
                        if len(data_recv) == 1:  # stimulator parameters
                            data_recv = np.append(data_recv, 0)

                        if self.address_2bytes.get(data_recv[0]):  # 2 bytes value
                            if len(data_recv) > 2:
                                data_recv = np.array([data_recv[0], self._char2int(data_recv[1:])])

                        if self.address.get(data_recv[0]):  # filtering parameters or sampling frequency
                            self.filter_parameters_queue.put(data_recv.astype(int))  # put for changing filter object
                        else:
                            self.change_parameter_queue.put(data_recv[:2].astype(int))  # put for changing classification parameters

                        if data_recv[0] == self.address_sampling_frequency:  # put sampling frequency to classification obj as well
                            self.change_parameter_queue.put(data_recv.astype(int))
                        # self.change_parameter_event.set()  # flag to notify there's a change of parameters is needed

                    if self.stop_event.is_set():
                        break

                client_socket_obj.close()
                self.raw_buffer_event.clear()  # stop inserting buffer

                count = 0

            count += 1

            if self.stop_event.is_set():
                break

        print('data bypassing thread has stopped...')

    def _char2int(self, data):
        output = [chr(int(x)) for x in data]
        output = ''.join(output)
        output = np.frombuffer(output, dtype=np.uint16)
        return int(output)





