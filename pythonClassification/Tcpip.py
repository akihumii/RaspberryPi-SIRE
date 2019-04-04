import numpy as np
import socket
from time import sleep


class TcpIp:
    def __init__(self, ip_add, port, buffer_size):
        self.ip_add = ip_add
        self.port = port

        self.buffer_size = buffer_size
        self.socket_obj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_obj.settimeout(2)

    def connect(self):  # connect to port
        self.socket_obj.connect((self.ip_add, self.port))
        print("Successfully connected...")

    def close(self):
        self.socket_obj.close()

    def read(self, buffer_leftover):  # read data from port
        num_bytes_recorded = 0
        buffer_read = np.array([], dtype=np.uint8)
        while num_bytes_recorded < self.buffer_size:
            try:
                buffer_part = self.socket_obj.recv(self.buffer_size - num_bytes_recorded)
            except socket.timeout:
                print("Data receive timeout...")
                break

            if buffer_part == '':
                print('Not received anything...')
                sleep(1)
            else:
                buffer_read = np.append(buffer_read, np.frombuffer(buffer_part, dtype=np.uint8))

                num_bytes_recorded = num_bytes_recorded + len(buffer_part)

        return np.append(buffer_leftover, buffer_read)

    def send(self, msg):
        total_sent = 0
        while total_sent < len(msg):
            sent = self.socket_obj.send(msg[total_sent:])
            if sent == 0:
                raise RuntimeError("Socket connection broken...")
            total_sent = total_sent + sent

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
        except socket.timeout:
            print("No connection has been established due to timeout...")
