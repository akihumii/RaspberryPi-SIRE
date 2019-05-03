import multiprocessing
import os
import numpy as np
import pickle
import time
from saving import Saving
from classification_decision import ClassificationDecision
from features import Features


class ProcessClassification(multiprocessing.Process, ClassificationDecision):
    def __init__(self, odin_obj, pin_reset_obj, thresholds, method_classify, features_id,  method_io, pin_led, channel_len, window_class, window_overlap, sampling_freq, ring_event, ring_queue, process_obj):
        multiprocessing.Process.__init__(self)
        ClassificationDecision.__init__(self, method_io, pin_led, 'out')

        self.clf = None
        self.window_class = window_class  # seconds
        self.window_overlap = window_overlap  # seconds
        self.sampling_freq = sampling_freq
        self.ring_event = ring_event
        self.ring_queue = ring_queue
        self.features_id = features_id
        self.process_obj = process_obj

        method_classify_all = {
            'features': self.classify_features,
            'thresholds': self.classify_thresholds
        }
        self.classify_function = method_classify_all.get(method_classify)

        self.thresholds = thresholds

        self.__channel_len = channel_len

        self.data = []
        self.channel_decode = []
        self.saving_file_all = Saving()

        self.odin_obj = odin_obj
        self.prediction = 0

        self.pin_reset_obj = pin_reset_obj

        self.start_classify_flag = False
        self.start_stimulation_flag = False
        self.flag_reset = False

    def run(self):
        self.setup()  # setup GPIO/serial classification display output
        self.load_classifier()  # load classifier

        print('started classification thread...')
        while True:
            if not self.start_stimulation_flag and self.process_obj.input_GPIO():  # send starting sequence to stimulator
                print('started stimulation...')
                self.start_stimulation_flag = True
                self.odin_obj.send_start_sequence()  # send start bit to odin
                self.update_channel_enable()  # send a channel enable that is the current prediction
                saving_file = Saving()

            # start classifying when data in ring queue has enough data
            if not self.start_classify_flag:
                self.start_classify_flag = np.size(self.data, 0) > (self.window_overlap * self.sampling_freq)

            while not self.ring_queue.empty():  # loop until ring queue has some thing
                self.data = self.ring_queue.get()
                # print(self.data[-1, 11])  # print counter
                # self.saving_file_all.save(self.data, "a")  # save filtered data in Rpi

                if self.start_classify_flag:
                    command_temp = self.classify()  # do the prediction and the output

                    command_array = np.zeros([np.size(self.data, 0), 2])  # create an empty command array
                    command_array[0, :] = command_temp

                    counter = self.data[:, 11][np.newaxis].T  # get the vertical matrix of counter

                    if self.start_stimulation_flag:
                        saving_file.save(np.append(counter, command_array, axis=1), "a")  # save the counter and the command

            if self.start_stimulation_flag and not self.process_obj.input_GPIO():  # send ending sequence to setimulator
                print('stopped stimulation...')
                self.start_stimulation_flag = False
                self.odin_obj.send_stop_sequence()  # send stop bit to odin

            if not self.flag_reset and self.pin_reset_obj.input_GPIO():  # reload parameters
                self.flag_reset = True
                self.thresholds = np.genfromtxt('thresholds.txt', delimiter=',', defaultfmt='%f')
                self.odin_obj.get_coefficients()
                self.odin_obj.send_parameters()
                time.sleep(0.04)
                self.update_channel_enable()
                print('thresholds have been reset...')
                print(self.thresholds)
                time.sleep(0.1)

            if self.flag_reset and not self.pin_reset_obj.input_GPIO():
                self.flag_reset = False
                print('reset flag changed to False...')
                time.sleep(0.1)

    def load_classifier(self):
        filename = sorted(x for x in os.listdir('classificationTmp') if x.startswith('classifier'))

        self.channel_decode = [x[x.find('Ch')+2] for x in filename]

        self.clf = [pickle.load(open(os.path.join('classificationTmp', x), 'rb')) for x in filename]

    def classify(self):
        prediction_changed_flag = False
        for i, x in enumerate(self.channel_decode):
            try:
                prediction = self.classify_function(i, self.data[:, int(x) - 1])  # pass in the channel index and data
                if prediction != (self.prediction >> i & 1):  # if prediction changes
                    self.prediction = self.output(i, prediction, self.prediction)  # function of classification_decision
                    prediction_changed_flag = True

            except ValueError:
                print('prediction failed...')

        if prediction_changed_flag:
            if self.start_stimulation_flag:  # send command to odin if the pin is pulled to high
                command = self.update_channel_enable()
                print('sending command to odin...')
                print(command)
                # print(self.odin_obj.amplitude)
                return command
            else:
                print('Prediction: %s' % format(self.prediction, 'b'))  # print new prediction
                return [0, 0]
        else:
            return [0, 0]

    def update_channel_enable(self):
        self.odin_obj.channel_enable = self.prediction
        command = self.odin_obj.send_channel_enable()
        return command

    def classify_features(self, channel_i, data):
        features = self.extract_features(data)
        prediction = self.clf[channel_i].predict([features]) - 1
        return prediction

    def classify_thresholds(self, channel_i, data):
        prediction = data >= self.thresholds[channel_i]
        prediction = any(prediction)
        return int(prediction)

    def extract_features(self, data):
        feature_obj = Features(data, self.sampling_freq, self.features_id)
        features = feature_obj.extract_features()
        return features



