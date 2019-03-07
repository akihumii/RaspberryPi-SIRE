#!/usr/bin/env python
import time
import serial

try:
        ser = serial.Serial(
                port='/dev/ttyACM0',  # Replace ttyS0 with ttyAM0 for Pi1,Pi2,Pi0
                baudrate=19200,
                timeout=1
        )
except serial.serialutil.SerialException:
        ser = serial.Serial(
                port='/dev/ttyACM1',  # Replace ttyS0 with ttyAM0 for Pi1,Pi2,Pi0
                baudrate=19200,
                timeout=1
        )



time.sleep(1)

channel_1 = 1
channel_2 = 1 << 1
channel_3 = 1 << 2
channel_4 = 1 << 3

while True:
        for x in range(16):
                # time.sleep(1)
                ser.write('%d\n' % x)
                print('Sent %d...' % x)
                time.sleep(1)
#         ser.write('%d' % (channel_1 | channel_3))
#         print('Sent %s...' % ser.read_until())
#         time.sleep(1)