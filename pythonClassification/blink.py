import time
import numpy as np
import RPi.GPIO as GPIO

# Pin definitions
led_pin = [[18, 4],
           [6, 13]]

# Use "GPIO" pin numbering
GPIO.setmode(GPIO.BCM)

# Set LED pin as output
for x in np.reshape(led_pin, np.size(led_pin)):
    GPIO.setup(x, GPIO.OUT)

# Blink forever
try:
    while True:
        for x in led_pin:
            for y in x:
                GPIO.output(y, GPIO.HIGH)  # Turn LED on
            time.sleep(1)                   # Delay for 1 second

            for y in x:
                GPIO.output(y, GPIO.LOW)  # Turn LED off
            time.sleep(1)                   # Delay for 1 second

# When you press ctrl+c, nicely release GPIO resources
finally:
    GPIO.cleanup()
