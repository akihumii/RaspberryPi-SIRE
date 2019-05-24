from config_serial import ConfigSerial
from config_GPIO import ConfigGPIO
from tcpip import TcpIp
import bitwise_operation
import time
import numpy as np


class ClassificationDecision(ConfigGPIO, TcpIp):
    def __init__(self, method, pin_led, mode):
        ConfigGPIO.__init__(self, pin_led, mode)
        self.method = method
        self.mode = self.mode
        self.obj = []
        self.result = 0

    def output(self, channel_index, state, value):
        if state:
            self.result = bitwise_operation.set_bit(value, channel_index)
        else:
            self.result = bitwise_operation.clear_bit(value, channel_index)

        switcher_output = {
            'GPIO': self.output_GPIO,
            'serial': self.obj.output_serial,
        }

        try:
            switcher_output.get(self.method)(self.result)
        except AttributeError:
            pass

        return self.result

    def output_serial_direct(self, data):
        # try:
            len_ser = len(self.obj.ser)
            if len_ser == 1:
                self.obj.output_serial(data)
            elif len_ser == 2:
                temp = np.zeros(2, dtype=int)
                if data == 0:
                    self.obj.output_serial(0, i=0)
                    self.obj.output_serial(0, i=1)
                if data >> 0 & 1:
                    temp[0] = bitwise_operation.set_bit(temp[0], 0)
                elif data >> 0 & 0:
                    temp[0] = bitwise_operation.clear_bit(temp[0], 0)

                if data >> 1 & 1:
                    temp[0] = bitwise_operation.set_bit(temp[0], 2)
                elif data >> 1 & 0:
                    temp[0] = bitwise_operation.clear_bit(temp[0], 2)

                if data >> 2 & 1:
                    temp[1] = bitwise_operation.set_bit(temp[1], 0)
                elif data >> 2 & 0:
                    temp[1] = bitwise_operation.clear_bit(temp[1], 0)

                if data >> 3 & 1:
                    temp[1] = bitwise_operation.set_bit(temp[1], 2)

                elif data >> 3 & 0:
                    temp[1] = bitwise_operation.clear_bit(temp[1], 2)

                print(temp)
                [self.obj.output_serial(x, i) for i, x in enumerate(temp)]

        # except AttributeError:
        #     print('AttributeError happened...')
        #     pass

    def input(self):
        switcher_output = {
            'GPIO': self.input_GPIO,
            'serial': self.input_serial
        }

        return switcher_output.get(self.method)()

    def setup(self):
        if self.method == "GPIO":
            self.setup_GPIO()()
        elif self.method == "serial":
            self.obj = ConfigSerial(self.mode)
            self.obj.setup_serial()
        else:
            print("Invalid method_io...")

    def stop(self):
        switcher_output = {
            'GPIO': self.stop_GPIO,
            'serial': self.stop_serial
        }

        switcher_output.get(self.method)()




