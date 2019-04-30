import socket
import random
import string
import time
from threading import *

host = "127.0.0.2"
port = 8000


class ClientSend(Thread):
    def __init__(self, ip_add, port):
        Thread.__init__(self)
        print('creating client...')
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ip_add = ip_add
        self.port = port
        try:
            self.start()
        except socket.error:
            time.sleep(2)

    def run(self):
        self.sock.connect((self.ip_add, self.port))
        while True:
            msg = random_string()
            totalsent = 0
            print('sending %s...' % msg)
            while totalsent < len(msg):
                sent = self.sock.send(msg[totalsent:])
                if sent == 0:
                    raise RuntimeError("socket connection broken")
                totalsent = totalsent + sent
            print('finished sending %s...' % msg)

            time.sleep(2)


class Client(Thread):
    def __init__(self, socket):
        Thread.__init__(self)
        self.sock = socket
        self.start()

    def run(self):
        while 1:
            print('Client sent:', self.sock.recv(1024))
            self.sock.send(b'Oi you sent something to me')


def random_string(string_length=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(string_length))


def create_client():
    ClientSend(host, port)  # create client and send something
    print('sending something...')


def listen_socket():
    obj_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    obj_socket.bind((host, port))
    print('socket bound...')
    obj_socket.listen(5)
    print('socket listening...')

    while 1:
        clientsocket, address = obj_socket.accept()  # waiting for connection
        print('Client connected...')
        Client(clientsocket)  # receive msg from client
        time.sleep(4)


if __name__ == "__main__":
    listen_socket()
    create_client()
