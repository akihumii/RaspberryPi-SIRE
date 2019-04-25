from numba.decorators import jit
import threading
from saving import Saving
from classification_decision import ClassificationDecision


class ReadNDemultiplex(ClassificationDecision, Saving):
    # @jit
    def __init__(self, tcp_ip_sylph, data_obj, ring_lock):
        Saving.__init__(self)
        self.data_obj = data_obj
        self.tcp_ip_sylph = tcp_ip_sylph
        self.ring_lock = ring_lock
        self.buffer_leftover = []

        self.empty_buffer_flag = True

    # def run(self):





