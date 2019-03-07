import numpy as np
import serial


class ConfigSerial:
    def __init__(self, mode):
        self.ser = None
        self.mode = mode

    def output_serial(self, data):
        self.ser.write('%d\n' % data)
        # print('Sent %d...' % data)

    def input_serial(self):
        return self.ser.readline()

    def stop_serial(self):
        pass

    def setup_serial(self):
        switcher_setup = {
            'out': '/dev/ttyACM',
            'in': '/dev/ttyUSB'
        }

        port = switcher_setup.get(self.mode)

        try:
            for x in range(4):
                self.ser = serial.Serial(
                    port='%s%d' % (port, x),  # Replace ttyS0 with ttyAM0 for Pi1,Pi2,Pi0
                    baudrate=19200,
                    timeout=1
                )
        except serial.serialutil.SerialException:
            print('No serial port is activated...')
            raise
