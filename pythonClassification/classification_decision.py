from numba.decorators import jit
from config_serial import ConfigSerial
from config_GPIO import ConfigGPIO
from tcpip import TcpIp


@jit
class ClassificationDecision(ConfigGPIO, ConfigSerial, TcpIp):
    def __init__(self, method, pin_led, mode, ip_add, port):
        ConfigGPIO.__init__(self, pin_led, mode)
        ConfigSerial.__init__(self, mode)
        TcpIp.__init__(self, ip_add, port, buffer_size=None)
        self.method = method
        self.result = 0

    def output(self, channel_index, state, value):
        if state:
            self.result = self.set_bit(value, channel_index)
        else:
            self.result = self.clear_bit(value, channel_index)

        switcher_output = {
            'GPIO': self.output_GPIO,
            'serial': self.output_serial
        }

        switcher_output.get(self.method)(self.result)

        return self.result

    def input(self):
        switcher_output = {
            'GPIO': self.input_GPIO,
            'serial': self.input_serial
        }

        return switcher_output.get(self.method)()

    def setup(self):
        switcher_setup = {
            'GPIO': self.setup_GPIO,
            'serial': self.setup_serial
        }

        switcher_setup.get(self.method)()

    def stop(self):
        switcher_output = {
            'GPIO': self.stop_GPIO,
            'serial': self.stop_serial
        }

        switcher_output.get(self.method)()

    def set_bit(self, value, index):
        return value | 1 << index

    def clear_bit(self, value, index):
        return value & ~(1 << index)



