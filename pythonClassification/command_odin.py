import numpy as np
import time
import bitwise_operation


class CommandOdin:
    def __init__(self, socket):
        self.address = {
            'amplitude_ch1':        0xF1,
            'amplitude_ch2':        0xF2,
            'amplitude_ch3':        0xF3,
            'amplitude_ch4':        0xF4,
            'frequency':            0xF5,
            'pulse_duration_ch1':   0xF6,
            'pulse_duration_ch2':   0xF7,
            'pulse_duration_ch3':   0xF9,
            'pulse_duration_ch4':   0xFA,
            'channel_enable':       0xFB,
            'step_increase':        0xFC,
            'step_decrease':        0xFD,
            'threshold_enable':     0xFE,
        }

        self.command_start = self._convert_to_char([0xF8, 0xF8])
        self.command_stop = self._convert_to_char([0x8F, 0x8F])

        self.amplitude_default = 5 * np.ones(4, dtype=np.double)

        self.amplitude = self.amplitude_default
        self.channel_enable = 0
        self.pulse_duration = 200 * np.ones(4, dtype=int)
        self.frequency = 50

        self.num_channel = 4

        self.amplitude_a = 0.0121
        self.amplitude_b = 12.853
        self.amplitude_c = 6.6892

        self.sock = socket

    def send_start_sequence(self):  # send all parameters except channel enable
        time.sleep(0.2)
        self.send_start()
        self.get_coefficients()
        self.amplitude = self.amplitude_default
        time.sleep(1)
        for i in range(self.num_channel):
            self.send_pulse_duration(i)
            time.sleep(0.04)
        for i in range(self.num_channel):
            self.send_amplitude(i)
            time.sleep(0.04)
        self.send_frequency()

    def send_stop_sequence(self):  # send stop sequence
        time.sleep(0.2)
        self.channel_enable = 0
        self.amplitude = np.zeros(4, dtype=np.double)
        for i in range(self.num_channel):
            self.send_amplitude(i)
            time.sleep(0.04)
        self.send_channel_enable()
        time.sleep(0.2)
        self.send_stop()

    def send_start(self):
        self.sock.send(self.command_start)

    def send_stop(self):
        self.sock.send(self.command_stop)

    def send_amplitude(self, channel):
        address = self.address.get('amplitude_ch%d' % int(channel+1))
        amplitude = self._get_amplitude_byte(channel)
        if amplitude > 240:  # set a upper limit
            amplitude = 240

        self.sock.send(self._convert_to_char([address, amplitude]))

    def send_pulse_duration(self, channel):
        address = self.address.get('pulse_duration_ch%d' % int(channel+1))
        self.sock.send(self._convert_to_char([address, self._get_pulse_duration_byte([channel])]))

    def send_frequency(self):
        address = self.address.get('frequency')
        self.sock.send(self._convert_to_char([address, self.frequency]))

    def send_channel_enable(self):
        address = self.address.get('channel_enable')
        self.sock.send(self._convert_to_char([address, self.channel_enable]))

    def get_coefficients(self):
        coefficients = np.genfromtxt('formula.txt', delimiter=',', defaultfmt='%f')
        self.amplitude_a = coefficients[0]
        self.amplitude_b = coefficients[1]
        self.amplitude_c = coefficients[2]

    def _get_pulse_duration_byte(self, channel):
        output = int(np.array(self.pulse_duration[channel]/5 - 3))
        return output

    def _get_amplitude_byte(self, channel):
        if self.amplitude[channel] == 0:
            output = int(0)
        else:
            output = self.amplitude[channel]**2*self.amplitude_a + self.amplitude[channel]*self.amplitude_b - self.amplitude_c  # the conversion into bytes
            output = int(output)
        return output

    def _convert_to_char(self, data):
        output = [chr(x) for x in data]
        output = ''.join(output)
        return output



