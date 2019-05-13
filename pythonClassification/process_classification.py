import multiprocessing
import os
import numpy as np
import pickle
import time
from saving import Saving
from classification_decision import ClassificationDecision
from features import Features


class ProcessClassification(multiprocessing.Process, ClassificationDecision):
    def __init__(self, odin_obj, pin_sm_channel_obj, pin_reset_obj, pin_save_obj, thresholds, method_classify, features_id,  method_io, pin_led, channel_len, window_class, window_overlap, sampling_freq, ring_event, ring_queue, pin_stim_obj, change_parameter_queue, change_parameter_event, stop_event):
        multiprocessing.Process.__init__(self)
        ClassificationDecision.__init__(self, method_io, pin_led, 'out')

        self.clf = None
        self.window_class = window_class  # seconds
        self.window_overlap = window_overlap  # seconds
        self.sampling_freq = sampling_freq
        self.ring_event = ring_event
        self.ring_queue = ring_queue
        self.features_id = features_id
        self.pin_stim_obj = pin_stim_obj
        self.pin_sm_channel_obj = pin_sm_channel_obj

        method_classify_all = {
            'features': self.classify_features,
            'thresholds': self.classify_thresholds
        }
        self.classify_function = method_classify_all.get(method_classify)

        self.thresholds = thresholds

        self.__channel_len = channel_len

        self.data = []
        self.channel_decode = []
        self.channel_decode_default = np.array([4, 5, 6, 7])
        self.saving_file_all = Saving()

        self.odin_obj = odin_obj
        self.prediction = 0

        self.pin_reset_obj = pin_reset_obj

        self.pin_save_obj = pin_save_obj
        self.saving_file = Saving()

        self.start_stimulation_address = 111
        self.stop_stimulation_address = 222
        self.start_stimulation_initial = False
        self.stop_stimulation_initial = False

        self.stimulation_close_loop_flag = False

        self.change_parameter_queue = change_parameter_queue
        self.change_parameter_event = change_parameter_event
        self.stop_event = stop_event

        self.address = {
            0xF1: self.update_amplitude,
            0xF2: self.update_amplitude,
            0xF3: self.update_amplitude,
            0xF4: self.update_amplitude,
            0xF5: self.update_frequency,
            0xF6: self.update_pulse_duration,
            0xF7: self.update_pulse_duration,
            0xF9: self.update_pulse_duration,
            0xFA: self.update_pulse_duration,
            0xFC: self.update_step_size
        }

        self.start_classify_flag = False
        self.start_stimulation_flag = False
        self.flag_multi_channel = False
        self.flag_reset = False
        self.flag_save_new = False

    def run(self):
        self.setup()  # setup GPIO/serial classification display output
        self.load_classifier()  # load classifier

        print('started classification thread...')
        while True:
            self.check_saving_flag()
            self.check_stimulation_flag()
            self.check_reset_flag()
            self.check_classify_dimension()
            self.check_change_parameter()

            # start classifying when data in ring queue has enough data
            if not self.start_classify_flag:
                self.start_classify_flag = np.size(self.data, 0) > (self.window_overlap * self.sampling_freq)

            while not self.ring_queue.empty():  # loop until ring queue has some thing
                self.data = self.ring_queue.get()
                # print(self.data[-1, 11])  # print counter
                # self.saving_file_all.save(self.data, "a")  # save filtered data in Rpi

                if self.start_classify_flag:
                    command_temp = self.classify()  # do the prediction and the display it

                    if not self.flag_save_new:
                        command_array = np.zeros([np.size(self.data, 0), 12])  # create an empty command array
                        command_array[0, 0:2] = command_temp  # replace the first row & second and third column with [address, value]
                        if self.start_stimulation_initial:
                            command_array[1, 0] = self.start_stimulation_address  # replace the second row first column with starting address
                            self.start_stimulation_initial = False
                        elif self.stop_stimulation_initial:
                            command_array[1, 0] = self.stop_stimulation_address  # replace the second row first column with starting address
                            self.stop_stimulation_initial = False

                        command_array[:, 2] = self.prediction  # replace the forth column with the current prediction
                        if self.start_stimulation_flag:
                            command_array[:, 3:7] = self.odin_obj.amplitude
                            command_array[:, 7:11] = self.odin_obj.pulse_duration
                            command_array[:, 11] = self.odin_obj.frequency
                        else:
                            command_array[:, 3:11] = 0

                        # counter = np.vstack(self.data[:, 11])  # get the vertical matrix of counter

                        self.saving_file.save(np.hstack([self.data, command_array]), "a")  # save the counter and the command
            if self.stop_event.is_set():
                break
        print('classify thread has stopped...')

    def update_step_size(self, data):
        self.odin_obj.step_size = data[1]
        print('updated step size...')
        print(data)
        time.sleep(0.4)

    def update_frequency(self, data):
        self.odin_obj.frequency = data[1]
        self.odin_obj.send_frequency()
        print('updated frequency...')
        print(data)
        time.sleep(0.04)

    def update_amplitude(self, data):
        address = {
            0xF1: 0,
            0xF2: 1,
            0xF3: 2,
            0xF4: 3
        }
        channel_id = address.get(data[0])
        self.odin_obj.amplitude[channel_id] = data[1]
        self.odin_obj.send_amplitude(channel_id)
        print('updated amplitude...')
        print(data)
        time.sleep(0.04)

    def update_pulse_duration(self, data):
        address = {
            0xF6: 0,
            0xF7: 1,
            0xF9: 2,
            0xFA: 3
        }
        channel_id = address.get(data[0])
        self.odin_obj.pulse_duration[channel_id] = data[1]
        self.odin_obj.send_pulse_duration(channel_id)
        print('updated pulse duration...')
        print(data)
        time.sleep(0.04)

    def check_change_parameter(self):
        if self.change_parameter_event.is_set():
            while not self.change_parameter_queue.empty():
                try:
                    data_parameter = self.change_parameter_queue.get()
                    # print(data_parameter)
                    self.address.get(data_parameter[0])(data_parameter)
                    self.change_parameter_event.clear()
                except TypeError:
                    print('failed to update the command:')
                    print(data_parameter)

    def check_classify_dimension(self):
        if not self.flag_multi_channel and self.pin_sm_channel_obj.input_GPIO():  # switch to multi-channel classification
            self.flag_multi_channel = True
            time.sleep(0.1)
            self.load_classifier()
            print('switched to multi-channel classification mode...')

        if self.flag_multi_channel and not self.pin_sm_channel_obj.input_GPIO():  # switch to single-channel classification
            self.flag_multi_channel = False
            time.sleep(0.1)
            self.load_classifier()
            print('switch to single-channel classification mode...')

    def check_reset_flag(self):
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

    def check_stimulation_flag(self):
        if not self.start_stimulation_flag and self.pin_stim_obj.input_GPIO():  # send starting sequence to stimulator
            print('started stimulation...')
            self.start_stimulation_flag = True  # start the stimulation
            self.start_stimulation_initial = True  # to insert initial flag in saved file
            self.odin_obj.send_start_sequence()  # send start bit to odin
            self.update_channel_enable()  # send a channel enable that is the current prediction

        if self.start_stimulation_flag and not self.pin_stim_obj.input_GPIO():  # send ending sequence to setimulator
            print('stopped stimulation...')
            self.start_stimulation_flag = False
            self.stop_stimulation_initial = True
            self.odin_obj.send_stop_sequence()  # send stop bit to odin

    def check_saving_flag(self):
        if not self.flag_save_new and self.pin_save_obj.input_GPIO():  # start a new file to save
            self.saving_file = Saving()
            self.flag_save_new = True
            print('stop saving...')
            time.sleep(0.1)

        if self.flag_save_new and not self.pin_save_obj.input_GPIO():
            self.flag_save_new = False
            print('resume saving with a new file...')
            time.sleep(0.1)

    def load_classifier(self):
        if self.pin_sm_channel_obj.input_GPIO():  # multi-channel classification
            filename = sorted(x for x in os.listdir('classificationTmp') if x.endswith('Cha.sav'))
            # self.channel_decode = [x[x.find('Ch') + 2] for x in filename]
            self.clf = pickle.load(open(os.path.join('classificationTmp', filename[0]), 'rb'))  # there should only be one classifier file
        else:  # single-channel classification
            filename = sorted(x for x in os.listdir('classificationTmp') if x.startswith('classifier') and not x.endswith('Cha.sav'))
            self.channel_decode = [x[x.find('Ch') + 2] for x in filename]  # there should be multiple classifier files
            self.clf = [pickle.load(open(os.path.join('classificationTmp', x), 'rb')) for x in filename]
        print('loaded classifier...')
        print(filename)

    def classify(self):
        prediction_changed_flag = False
        if self.pin_sm_channel_obj.input_GPIO():  # multi-channel classification
            # try:
                prediction = self.classify_function('all', self.data[:, self.channel_decode_default-1])  # pass in the channel index and data
                if prediction != self.prediction:  # if prediction changes
                    for i in range(self.odin_obj.num_channel):
                        self.output(i, prediction, self.prediction)  # function of classification_decision
                    prediction_changed_flag = True
                self.prediction = prediction

            # except ValueError:
            #     print('prediction failed...')
        else:
            for i, x in enumerate(self.channel_decode):
                try:
                    prediction = self.classify_function(i, self.data[:, int(x) - 1])  # pass in the channel index and data
                    if prediction != (self.prediction >> i & 1):  # if prediction changes
                        self.prediction = self.output(i, prediction, self.prediction)  # function of classification_decision
                        prediction_changed_flag = True

                except ValueError:
                    print('prediction failed...')

        if prediction_changed_flag:  # send command when there is a change in prediction
            if self.start_stimulation_flag:  # send command to odin if the pin is pulled to high
                if self.stimulation_close_loop_flag:
                    command = self.odin_obj.send_step_size_increase()
                else:
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
        if channel_i == 'all':  # for the case of multi-channel decoding
            prediction = self.clf.predict([features]) - 1
        else:
            prediction = self.clf[channel_i].predict([features]) - 1
        return prediction

    def classify_thresholds(self, channel_i, data):
        if channel_i == 'all':  # for the case of multi-channel decoding
            prediction = data >= self.thresholds
            prediction = prediction.any()
        else:
            prediction = data >= self.thresholds[channel_i]
            prediction = any(prediction)
        return int(prediction)

    def extract_features(self, data):
        feature_obj = Features(data, self.sampling_freq, self.features_id)
        features = feature_obj.extract_features()
        return features



