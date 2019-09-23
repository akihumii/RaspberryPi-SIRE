import numpy as np
import serial
import sys, errno


class ConfigSerial:
    def __init__(self, mode):
        self.ser = None
        self.mode = mode

    def output_serial(self, data, i=0):
        print('writing data %d: %d...' % (i, data))
        try:
            self.ser[i].write('%d\n' % data)
        except serial.SerialException:
            print('failed to send data %d\n' % data)
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

        ser_temp = []
        for x in range(4):
            try:
                ser_temp = np.append(ser_temp, serial.Serial(
                    port='%s%d' % (port, x),  # Replace ttyS0 with ttyAM0 for Pi1,Pi2,Pi0
                    baudrate=19200,
                    timeout=1
                ))
                print('Connected to %s%d' % (port, x))
            except serial.serialutil.SerialException:
                print('No serial port is activated...')
        self.ser = ser_temp

