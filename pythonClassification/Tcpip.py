from numba.decorators import jit
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
            self.socket_obj.bind((self.ip_add, self.port))
            self.bound_flag = True
        while True:
            try:
                while True:
                    self.socket_obj.listen(2)
                    print('socket listening...')
                    client_socket, address = self.socket_obj.accept()  # waiting for connection
                    print('Client connected...')
                    sleep(1)

                    return client_socket

            except socket.timeout:
                print('connection time out...')
                return []

    def connect(self):  # connect to port
        self.socket_obj.connect((self.ip_add, self.port))
        print("Successfully connected...")

    def close(self):
        self.socket_obj.close()

    # @jit
    def read(self):  # read data from port
        num_bytes_recorded = 0
        buffer_part = ''
        while num_bytes_recorded < self.buffer_size:
            try:
                buffer_part = self.socket_obj.recv(self.buffer_size - num_bytes_recorded)
            except socket.timeout:
                print("Data receive timeout...")
                break

            num_bytes_recorded = num_bytes_recorded + len(buffer_part)

        return buffer_part

    @jit
    def send(self, msg):
        try:
            total_sent = 0
            while total_sent < len(msg):
                sent = self.socket_obj.send(msg[total_sent:])
                if sent == 0:
                    raise RuntimeError("Socket connection broken...")
                total_sent = total_sent + sent
            return 0
        except IOError as e:
            if e.errno == errno.EPIPE:
                return 1

    @jit
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
