from numba.decorators import jit
import RPi.GPIO as GPIO
import numpy as np


@jit
class Display:
    def __init__(self):
        self.led_pin = [[18, 4],
                        [17, 27],
                        [22, 5],
                        [6, 13]]
        GPIO.setmode(GPIO.BCM)  # Use "GPIO" pin numbering

        self.__setup()

    def display(self, channel_index, state):
        if state:
            for x in self.led_pin[channel_index]:
                GPIO.output(x, GPIO.HIGH)
        else:
            for x in self.led_pin[channel_index]:
                GPIO.output(x, GPIO.LOW)

    def switchoff(self):
        GPIO.cleanup()

    def __setup(self):
        try:
            for x in np.reshape(self.led_pin, np.size(self.led_pin)):
                GPIO.setup(x, GPIO.OUT)
        except RuntimeWarning:
            pass


