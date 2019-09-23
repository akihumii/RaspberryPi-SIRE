from tcpip import TcpIp

class ConfigCommand:
    def __init__(self, ip_add, port):
        self.tcpip_obj = TcpIp.__init__(ip_add, port)
        self.tcpip_obj.connect()

    def output_command(self, data):

    def input_command(self):
        return self.ser.readline()

    def stop_command(self):
        pass

    def setup_command(self):
