import multiprocessing
import os
import numpy as np
import pickle
from saving import Saving
from classification_decision import ClassificationDecision
from features import Features


class ProcessClassification(multiprocessing.Process, Saving, ClassificationDecision):
    def __init__(self, odin_obj, features_id,  method, pin_led, channel_len, window_class, window_overlap, sampling_freq, ring_event, ring_queue, process_obj):
        multiprocessing.Process.__init__(self)
        Saving.__init__(self)
        ClassificationDecision.__init__(self, method, pin_led, 'out')

        self.clf = None
        self.window_class = window_class  # seconds
        self.window_overlap = window_overlap  # seconds
        self.sampling_freq = sampling_freq
        self.ring_event = ring_event
        self.ring_queue = ring_queue
        self.features_id = features_id
        self.process_obj = process_obj

        self.__channel_len = channel_len

        self.data_raw = []
        self.channel_decode = []

        self.odin_obj = odin_obj
        self.prediction = 0

        self.start_stimulation_flag = False

    def run(self):
        self.setup()  # setup GPIO/serial classification display output
        self.load_classifier()  # load classifier

        print('started classification thread...')
        while True:
            if not self.start_stimulation_flag and self.process_obj.input_GPIO():
                print('started stimulation...')
                self.start_stimulation_flag = True
                # self.odin_obj.send_start_sequence()  # send start bit to odin

            while not self.ring_queue.empty():  # loop until ring queue has some thing
                self.data_raw = self.ring_queue.get()
                self.save(self.data_raw, "a")

            # start classifying when data in ring queue has enough data
            if np.size(self.data_raw, 0) > (self.window_overlap * self.sampling_freq):
                self.classify()  # do the prediction and the output

            if self.start_stimulation_flag and not self.process_obj.input_GPIO():
                print('stopped stimulation...')
                self.start_stimulation_flag = False
                # self.odin_obj.send_stop_sequence()  # send stop bit to odin

    def load_classifier(self):
        filename = sorted(x for x in os.listdir('classificationTmp') if x.startswith('classifier'))

        self.channel_decode = [x[x.find('Ch')+2] for x in filename]

        self.clf = [pickle.load(open(os.path.join('classificationTmp', x), 'rb')) for x in filename]

    def classify(self):
        for i, x in enumerate(self.channel_decode):
            feature_obj = Features(self.data_raw[int(x)-1], self.sampling_freq, self.features_id)
            features = feature_obj.extract_features()
            try:
                prediction = self.clf[i].predict([features]) - 1
                if prediction != (self.prediction >> i & 1):  # if prediction changes
                    self.prediction = self.output(i, prediction, self.prediction)  # function of classification_decision
                    print('Prediction: %s' % format(self.prediction, 'b'))
                    # if self.start_stimulation_flag:
                    #     self.odin_obj.channel_enable = self.prediction
                    #     self.odin_obj.send_channel_enable()
            except ValueError:
                print('prediction failed...')



