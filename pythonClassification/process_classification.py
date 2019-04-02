import multiprocessing
import os
import numpy as np
import pickle
from saving import Saving
from classification_decision import ClassificationDecision
from features import Features


class ProcessClassification(multiprocessing.Process, Saving, ClassificationDecision, Features):
    def __init__(self, method_saving, thresholds, method_classify, features_id,  method_io, pin_led, ip_add, port, channel_len, window_class, window_overlap, sampling_freq, ring_event, ring_queue):
        multiprocessing.Process.__init__(self)
        Saving.__init__(self, method=method_saving)
        ClassificationDecision.__init__(self, method_io, pin_led, 'out', ip_add, port)
        Features.__init__(sampling_freq, features_id)

        self.clf = None
        self.window_class = window_class  # seconds
        self.window_overlap = window_overlap  # seconds
        self.sampling_freq = sampling_freq
        self.ring_event = ring_event
        self.ring_queue = ring_queue
        self.features_id = features_id

        self.__channel_len = channel_len

        self.data = []
        self.channel_decode = []

        self.prediction = 0

    def run(self):
        self.setup()  # setup GPIO/serial classification display output
        self.load_classifier()
        while True:
            if not self.ring_event.is_set():
                print('pause processing...')
                break

            while not self.ring_queue.empty():  # loop until ring queue has some thing
                self.data = self.ring_queue.get()
                self.save(self.data, "a")

            # start classifying when data in ring queue has enough data
            if np.size(self.data, 0) > (self.window_overlap * self.sampling_freq):
                self.classify()  # do the prediction and the output

        self.stop()  # stop GPIO/serial classification display output

    def load_classifier(self):
        filename = sorted(x for x in os.listdir('classificationTmp') if x.startswith('classifier'))

        self.channel_decode = [x[x.find('Ch')+2] for x in filename]

        self.clf = [pickle.load(open(os.path.join('classificationTmp', x), 'rb')) for x in filename]

    def classify(self):
        for i, x in enumerate(self.channel_decode):
            features = self.extract_features(self.data[int(x)-1])
            try:
                prediction = self.clf[i].predict([features]) - 1
                if prediction != (self.prediction >> i & 1):  # if prediction changes
                    self.prediction = self.output(i, prediction, self.prediction)  # function of classification_decision
                    print('Prediction: %s' % format(self.prediction, 'b'))
            except ValueError:
                print('prediction failed...')



