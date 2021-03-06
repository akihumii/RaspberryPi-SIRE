from config_serial import ConfigSerial
from config_GPIO import ConfigGPIO
from tcpip import TcpIp
import bitwise_operation
import time
import numpy as np


class ClassificationDecision(ConfigGPIO, TcpIp):
    def __init__(self, method, pin_led, mode, robot_hand_output='4F'):
        ConfigGPIO.__init__(self, pin_led, mode)
        self.method = method
        self.mode = self.mode
        self.obj = []
        self.serial_len = 0
        self.result = 0
        self.robot_hand_output = robot_hand_output

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

    def output_serial_direct(self, data, index=-1):
        # try:
            if self.serial_len == 1:
                if self.robot_hand_output == 'combo':
                    self.combo(data, index)
                else:
                    self.obj.output_serial(data)
            elif self.serial_len == 2:
                if index == -1:
                    [self.obj.output_serial(x, i) for i, x in enumerate([15, 15])]
                else:
                    hand_dic = {
                        'PSS': self.PSS,
                        '4F': self.four_fingers,
                        'combo': self.combo
                    }
                    hand_dic.get(self.robot_hand_output)(data, index)
            else:
                pass

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
            self.serial_len = len(self.obj.ser)
        else:
            print("Invalid method_io...")

    def stop(self):
        switcher_output = {
            'GPIO': self.stop_GPIO,
            'serial': self.stop_serial
        }

        switcher_output.get(self.method)()

    def combo(self, data, index):
        print('converting %d' % data)
        action_dic = {
            0: 0,
            1: 3,
            2: 31,
            3: 21,
            4: 16,
            5: 7,
            6: 24,
            7: 17,
            8: 1,
            9: 19,
            10: 14,
            11: 27,
            12: 8,
            13: 9,
            14: 25,
            15: 2
        }
        [self.obj.output_serial(action_dic.get(data), i) for i in range(self.serial_len)]

    def PSS(self, data, index):  # paper-sicissors-stone settings
        if data >> 0 & 1 and data >> 1 & 1:
            self.obj.output_serial(0, 0)
            return
        if data >> 2 & 1 and data >> 3 & 1:
            self.obj.output_serial(0, 1)
            return
        if index == 0:
            if data >> index & 1:
                self.obj.output_serial(3, 0)
        elif index == 1:
            if data >> index & 1:
                self.obj.output_serial(15, 0)
        elif index == 2:
            if data >> index & 1:
                self.obj.output_serial(3, 1)
        elif index == 3:
            if data >> index & 1:
                self.obj.output_serial(15, 1)

    def four_fingers(self, data, index):
        temp = 0
        if data >> 0 & 1:
            temp = bitwise_operation.set_bit(temp, 0)
        elif data >> 0 & 0:
            temp = bitwise_operation.clear_bit(temp, 0)
        if data >> 1 & 1:
            temp = bitwise_operation.set_bit(temp, 2)
        elif data >> 1 & 0:
            temp = bitwise_operation.clear_bit(temp, 2)
        self.obj.output_serial(temp, 0)

        temp = 0
        if data >> 2 & 1:
            temp = bitwise_operation.set_bit(temp, 0)
        elif data >> 2 & 0:
            temp = bitwise_operation.clear_bit(temp, 0)
        if data >> 3 & 1:
            temp = bitwise_operation.set_bit(temp, 2)
        elif data >> 3 & 0:
            temp = bitwise_operation.clear_bit(temp, 2)
        self.obj.output_serial(temp, 1)





