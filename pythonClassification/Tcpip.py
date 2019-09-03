import numpy as np
import socket
import sys, errno
from time import sleep


class TcpIp:
    def __init__(self, ip_add, port, buffer_size):
        self.ip_add = ip_add
        self.port = port

        self.buffer_size = buffer_size
        self.socket_obj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_obj.settimeout(2)

        self.bound_flag = False

    def create_host(self):  # act as a host
        if not self.bound_flag:
            self.socket_obj.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket_obj.bind((self.ip_add, self.port))
            self.bound_flag = True
        while True:
            try:
                while True:
                    self.socket_obj.listen(2)
                    # print('socket listening...')
                    client_socket, address = self.socket_obj.accept()  # waiting for connection
                    print('Client connected...')
                    sleep(1)

                    return client_socket

            except socket.timeout:
                # print('connection time out...')
                return []

    def connect(self):  # connect to port
        self.socket_obj.connect((self.ip_add, self.port))
        print("Successfully connected...")

    def close(self):
        self.socket_obj.close()

    def read(self, buffer_leftover, data_type=''):  # read data from port
        num_bytes_recorded = 0
        buffer_read = np.array([], dtype=np.uint8)
        buffer_raw = ''
        count = 1
        while num_bytes_recorded < self.buffer_size:
            try:
                buffer_part = self.socket_obj.recv(self.buffer_size - num_bytes_recorded)
            except (socket.timeout, IOError), e:
                if e.errno != errno.EWOULDBLOCK:
                    print("Data receive timeout...")
                break

            if not buffer_part:
                pass
                # print('Not received anything...')
                # sleep(1)
            else:
                buffer_raw = ''.join([buffer_raw, buffer_part])
                if data_type == 'text':
                    buffer_read = np.append(buffer_read, buffer_part)
                else:
                    if data_type == 'single':
                        dt = np.dtype(np.float32)
                        dt = dt.newbyteorder('>')
                    elif data_type == 'double':
                        dt = np.dtype(np.float64)
                        dt = dt.newbyteorder('>')
                    else:
                        dt = np.uint8
                    buffer_read = np.append(buffer_read, np.frombuffer(buffer_part, dtype=dt))

                num_bytes_recorded = num_bytes_recorded + len(buffer_part)

            count += 1

            if count == 3 and not buffer_part and not buffer_part:
                # print('break receiving now...')
                break

        return np.append(buffer_leftover, buffer_read), ''.join(buffer_raw)

    def send(self, msg):
        try:
            total_sent = 0
            while total_sent < len(msg):
                sent = self.socket_obj.send(msg[total_sent:])
                if sent == 0:
                    raise RuntimeError("Socket connection broken...")
                total_sent = total_sent + sent
            # print('successfully sent...')
            return 0
        except IOError as e:
            if e.errno == errno.EPIPE:
                print('failed to send...')
                return 1

    def clear_buffer(self):
        try:
            packet = self.socket_obj.recv(self.buffer_size)
            while packet:
                packet = self.socket_obj.recv(self.buffer_size)
        except socket.timeout:
            pass

    def write_disconnect(self):
        msg = 'DISCONNECT!!!!!!'  # 16 char
        try:
            self.socket_obj.send(msg)
        except (socket.timeout, IOError) as e:
            if e.errno == errno.EPIPE:
                print('connection broken...')
            else:
                print("No connection has been established due to timeout...")
