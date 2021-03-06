import multiprocessing
import os
import numpy as np
import pickle
import time
import bitwise_operation
import glob
from saving import Saving
from classification_decision import ClassificationDecision
from features import Features


class ProcessClassification(multiprocessing.Process, ClassificationDecision):
    def __init__(self, odin_obj, pins_obj, param, ring_event, ring_queue, change_parameter_queue, change_parameter_event, stop_event, filename_queue, dyno_queue, num_class_value):

        multiprocessing.Process.__init__(self)
        ClassificationDecision.__init__(self, param.method_io, param.pin_led, 'out', param.robot_hand_output)

        self.clf = None
        self.num_class = 0
        self.num_class_value = num_class_value
        self.sampling_freq = param.sampling_freq
        self.hp_thresh = 0
        self.lp_thresh = 0
        self.notch_thresh = 0
        self.window_class = param.window_class  # seconds
        self.window_overlap = param.window_overlap  # seconds
        self.ring_event = ring_event
        self.ring_queue = ring_queue
        self.features_id = param.features_id
        self.pin_stim_obj = pins_obj.pin_stim_obj
        self.pin_sm_channel_obj = pins_obj.pin_sm_channel_obj
        self.method_io = param.method_io
        self.pin_sh_obj = pins_obj.pin_sh_obj  # software hardware object, HIGH for hardware, LOW for software
        self.pin_classify_method_obj = pins_obj.pin_classify_method_obj

        self.robot_hand_output = param.robot_hand_output

        self.method_classify_all = {
            'features': self.classify_features,
            'thresholds': self.classify_thresholds
        }
        self.classify_method = param.method_classify
        self.classify_function = self.method_classify_all.get(self.classify_method)

        self.__channel_len = param.channel_len

        self.data = []
        self.data_temp = []
        self.size_temp = 0
        self.norms = []
        self.channel_decode = []
        self.channel_decode_default = np.array([4, 5, 6, 7])
        self.num_channel = len(self.channel_decode_default)
        self.saving_file_all = Saving()

        self.odin_obj = odin_obj
        self.prediction = 0
        self.prediction_changed_flag = []

        self.extend_stim_orig = param.extend_stim  # extend the stimulation for a time
        self.extend_stim = []
        self.extend_stim_flag = np.zeros(self.num_channel, dtype=bool)

        self.pin_reset_obj = pins_obj.pin_reset_obj

        self.pin_save_obj = pins_obj.pin_save_obj
        self.saving_file = Saving()
        self.filename_queue = filename_queue

        self.dyno_queue = dyno_queue
        self.dyno_temp = 0

        self.pin_closed_loop_obj = pins_obj.pin_closed_loop_obj

        self.start_stimulation_address = 111
        self.stop_stimulation_address = 222
        self.real_channel_enable_address = 100
        self.real_channel_disable_address = 200
        self.start_stimulation_initial = False
        self.stop_stimulation_initial = False

        self.stimulation_close_loop_flag = False

        self.change_parameter_queue = change_parameter_queue
        self.change_parameter_event = change_parameter_event
        self.stop_event = stop_event

        self.address = {
            0xF8: self.update_on_off,
            0x8F: self.update_on_off,
            0xF1: self.update_amplitude,
            0xF2: self.update_amplitude,
            0xF3: self.update_amplitude,
            0xF4: self.update_amplitude,
            0xF5: self.update_frequency,
            0xF6: self.update_pulse_duration,
            0xF7: self.update_pulse_duration,
            0xF9: self.update_pulse_duration,
            0xFA: self.update_pulse_duration,
            0xFB: self.update_channel_enable,
            0xFC: self.update_step_size,
            0xC9: self.update_threshold_upper,
            0xCA: self.update_threshold_lower,
            0xCB: self.update_debounce_delay,
            0xCC: self.update_threshold_digit,
            0xCD: self.update_threshold_digit,
            0xCE: self.update_threshold_digit,
            0xCF: self.update_threshold_digit,
            0xD0: self.update_threshold_power,
            0xD1: self.update_threshold_power,
            0xD2: self.update_threshold_power,
            0xD3: self.update_threshold_power,
            0xD4: self.update_decoding_window_size,
            0xD5: self.update_overlap_window_size,
            0xD6: self.update_sampling_freq,
            0xD7: self.update_hp_thresh,
            0xD8: self.update_lp_thresh,
            0xD9: self.update_notch_thresh,
            0xDA: self.update_extend_stimulation,
            0xDB: self.update_classify_dimention,
            0xDC: self.update_closed_loop,
            0xDD: self.update_reset_flag,
            0xDE: self.update_stimulation_flag,
            0xDF: self.update_classify_methods,
            0xE0: self.update_saving_flag,
            0xE1: self.update_saving_transfer,
            0xE2: self.update_stimulation_pattern,
            0xE3: self.update_stimulation_pattern_flag
        }

        self.stim_threshold_upper = 10
        self.stim_threshold_lower = 10
        self.stim_debounce_delay = 10

        self.stim_threshold_digit = 1 * np.ones(np.shape(self.channel_decode_default), dtype=np.float)
        self.stim_threshold_power = 10 * np.ones(np.shape(self.channel_decode_default), dtype=np.float)
        self.stim_threshold = [x * 10 ** self.stim_threshold_power[i] for i, x in enumerate(self.stim_threshold_digit)]

        self.stim_pattern_input = []
        self.stim_pattern_output = []
        # self.stim_on = 1 << 0 | 1 << 1  # set channel 1 and 2 to control on
        # self.stim_target = 0
        # self.stim_target_temp = 0  # to store temporary prediction if no channel is activated

        self.start_stimulation_flag = False
        self.start_integration_flag = False
        self.real_channel_enable_flag = False
        self.real_channel_disable_flag = False
        self.flag_multi_channel = False
        self.flag_reset = False
        self.flag_save_new = True
        self.flag_closed_loop = False
        self.flag_classify_method = False
        self.flag_save_input_output = False
        # self.flag_stim_pattern = False  # False for normal stimulation, True for target stimulation

    def run(self):
        time.sleep(1)  # wait for other threads to start running
        self.setup()  # setup GPIO/serial classification display output
        self.load_classifier()  # load classifier

        print('started classification thread...')
        while True:  # loop until ring_queue is not empty
            self.check_change_parameter()
            self.check_filename()
            if not self.ring_queue.empty():
                self.data = self.ring_queue.get()
                break

        while True:  # loop unitl data size reach a certain length
            self.check_change_parameter()
            self.check_filename()
            if not self.ring_queue.empty():
                if np.size(self.data, 0) > self._get_window_class_sample_len():
                    self.data = self.data[-self._get_window_class_sample_len():, :]
                    break
                self.data = np.append(self.data, self.ring_queue.get(), axis=0)

        while True:
            self.check_change_parameter()
            self.check_filename()
            if self.pin_sh_obj.input_GPIO():
                self.check_saving_flag()
                self.check_stimulation_flag()
                self.check_reset_flag()
                self.check_classify_dimension()
                self.check_closed_loop()

            # start classifying when data in ring queue has enough data
            if not self.ring_queue.empty():  # loop until ring queue has some thing
                if len(self.data_temp) > 0:
                    self.data_temp = np.append(self.data_temp, self.ring_queue.get(), axis=0)
                else:
                    self.data_temp = self.ring_queue.get()

                self.size_temp = np.size(self.data_temp, 0)
                if self.size_temp > self._get_window_overlap_sample_len():
                    self.data = np.append(self.data, self.data_temp, axis=0)
                    self.data = self.data[self.size_temp:, :]  # pop out the a portion from self.data which has the size same as the data_temp
                    self.data_temp = []
                    # print(self.data[-1, 11])  # print counter
                    # self.saving_file_all.save(self.data, "a")  # save filtered data in Rpi

                    # print('start classifying...')
                    command_temp = self.classify()  # do the prediction and the display it

                    if not self.flag_save_new:
                        self.save_file(command_temp)

                # print('stop classifying...')
            if self.stop_event.is_set():
                break
        print('classify thread has stopped...')

    def classify(self):
        # Check prediction change flag
        if self.flag_multi_channel:  # multi-channel classification
            prediction = self.classify_function('all', self.data[:, self.channel_decode_default-1])  # pass in the channel index and data
        else:
            prediction = 0
            for i, x in enumerate(self.channel_decode):
                prediction_temp = self.classify_function(i, self.data[:, int(x) - 1])  # pass in the channel index and data
                prediction = bitwise_operation.edit_bit(i, prediction_temp, prediction)

        self.prediction_changed_flag = [(prediction >> i & 1) != (self.prediction >> i & 1) for i in range(self.num_channel)]

        self.check_extend_stim(prediction)

        if self.method_io == 'serial':
            if self.flag_multi_channel:  # multi-channel classification
                self.serial_output_4F(prediction)
            else:
                output_dic = {
                    'PSS': self.serial_output_PSS,
                    '4F': self.serial_output_4F,
                    'combo': self.serial_output_4F
                }
                output_dic.get(self.robot_hand_output)(prediction)
        else:
            for i, x in enumerate(self.prediction_changed_flag):
                if x:  # if prediction changes
                    self.prediction = self.output(i, prediction >> i & 1, self.prediction)  # function of classification_decision

        if self.start_integration_flag:  # send command to odin if the pin is pulled to high
            # if self.flag_closed_loop:  # closed-loop stimulation
            #     command = self.odin_obj.send_step_size_increase()
            #     print('sending command to odin...')
            #     print(command)
            #     # print(self.odin_obj.amplitude)
            #     return command
            # else:  # single stimulation
            if self.prediction_changed_flag is not None and any(self.prediction_changed_flag):  # send command when there is a change in prediction
                command = self.change_channel_enable()
                # print(self.odin_obj.amplitude)
                return command
            else:
                return [0, 0]
        else:
            if self.prediction_changed_flag is not None and any(self.prediction_changed_flag):  # send command when there is a change in prediction
                # print('prediction_change_flag:')
                # print(self.prediction_changed_flag)
                print('Prediction: %s' % format(self.prediction, 'b'))  # print new prediction
            else:
                return [0, 0]

    def serial_output_PSS(self, prediction):
        for i, x in enumerate(self.prediction_changed_flag):
            if x:
                self.output_serial_direct(prediction, i)
                self.prediction = bitwise_operation.edit_bit(i, (prediction >> i & 1), self.prediction)
                return np.ones(np.size(self.prediction_changed_flag), dtype=bool)

    def serial_output_4F(self, prediction):
        for i, x in enumerate(self.prediction_changed_flag):
            if x:  # if prediction changes
                self.prediction = bitwise_operation.edit_bit(i, prediction >> i & 1, self.prediction)  # function of classification_decision

    def save_file(self, command_temp):
        command_array = np.zeros([self.size_temp, 19])  # create an empty command array

        # if command_temp is not None:
        #     command_array[:, 1] = command_temp[1]  # replace the first row & second and third column with [address, value]
        if self.start_stimulation_initial:
            command_array[1, 0] = self.start_stimulation_address  # replace the second row first column with starting address
            self.start_stimulation_initial = False
        elif self.stop_stimulation_initial:
            command_array[1, 0] = self.stop_stimulation_address  # replace the second row first column with starting address
            self.stop_stimulation_initial = False

        if self.real_channel_enable_flag:
            command_array[0, 0] = self.real_channel_enable_address
            self.real_channel_enable_flag = False

        if self.real_channel_disable_flag:
            command_array[0, 0] = self.real_channel_disable_address
            self.real_channel_disable_flag = False

        # if any(self.prediction_changed_flag):
        # command_array[:, 0] = self.prediction

        # if self.start_integration_flag:
        #     if not self.pin_sh_obj.input_GPIO():  # software command
        command_array[:, 1] = self.odin_obj.channel_enable  # replace the forth column with odin channel enable
            # else:
        command_array[:, 2] = self.prediction  # replace the forth column with the current prediction
        # else:
        #     if not self.pin_sh_obj.input_GPIO():  # software command
        #         command_array[:, 1] = self.prediction  # replace the forth column with the current prediction
        #     else:
        #         command_array[:, 1] = self.odin_obj.channel_enable  # replace the forth column with odin channel enable

        command_array[:, 3:7] = self.odin_obj.amplitude
        command_array[:, 7:11] = self.odin_obj.pulse_duration

        command_array[:, 11] = self.odin_obj.frequency
        if self.classify_method == 'thresholds':
            command_array[:, 12:16] = self.stim_threshold

        if self.flag_save_input_output:
            command_array[0, 16] = self.flag_multi_channel + 1000
            if self.stim_pattern_input:
                command_array[1:len(self.stim_pattern_input)+1, 16] = self.stim_pattern_input
                command_array[1:len(self.stim_pattern_output)+1, 17] = self.stim_pattern_output
            self.flag_save_input_output = False
            
        if not self.dyno_queue.empty():
            temp_array = []
            while True:
                temp_array.extend(self.dyno_queue.get())
                if self.dyno_queue.empty():
                    break
            if temp_array:
                temp_locs = range(0, self.size_temp, int(np.ceil(np.float(self.size_temp)/len(temp_array))))
                for i in range(len(temp_locs)-1):
                    command_array[temp_locs[i]:temp_locs[i+1], 18] = temp_array[i]
                command_array[temp_locs[-1]:, 18] = temp_array[-1]
                self.dyno_temp = temp_array[-1]
        else:
            command_array[:, 18] = self.dyno_temp

        # counter = np.vstack(self.data[:, 11])  # get the vertical matrix of counter

        self.saving_file.save(np.hstack([self.data[-self.size_temp:, :], command_array]), "a")  # save the counter and the command

    def load_classifier(self):
        if self.flag_multi_channel:  # multi-channel classification
            filename = sorted(x for x in os.listdir('classificationTmp') if 'classifierCha' in x)
            # self.channel_decode = [x[x.find('Ch') + 2] for x in filename]
            self.num_class = int(filename[0][13])
            self.num_channel = self.odin_obj.num_channel
            self.clf = pickle.load(open(os.path.join('classificationTmp', filename[0]), 'rb'))  # there should only be one classifier file
            file_norms = [x for x in os.listdir('classificationTmp') if 'normsCha' in x]
            self.norms = np.genfromtxt(os.path.join('classificationTmp', file_norms[0]), delimiter=',')
        else:  # single-channel classification
            filename = sorted(x for x in os.listdir('classificationTmp') if x.startswith('classifier') and 'Cha' not in x)
            self.channel_decode = [x[x.find('Ch') + 2] for x in filename]  # there should be multiple classifier
            self.num_class = len(filename)
            self.num_channel = len(self.channel_decode)
            self.clf = [pickle.load(open(os.path.join('classificationTmp', x), 'rb')) for x in filename]
            file_norms = [x for x in os.listdir('classificationTmp') if x.startswith('normsCh') and 'Cha' not in x]
            self.norms = [np.genfromtxt(os.path.join('classificationTmp', x), delimiter=',') for x in file_norms]
        self.extend_stim = self.extend_stim_orig * np.ones(self.num_channel)
        self.extend_stim_flag = np.zeros(self.num_channel, dtype=bool)
        print('loaded classifier...')
        print(filename)

    def extract_features(self, data):
        feature_obj = Features(data, self.sampling_freq, self.features_id)
        return feature_obj.extract_features()

    def classify_features(self, channel_i, data):
        if channel_i == 'all':  # for the case of multi-channel decoding
            features = np.array([self.extract_features(data[:, i]) for i in range(len(self.channel_decode_default))])
            features = np.hstack(np.transpose(np.vstack(features)))  # reconstruct into correct structure
            features = features / self.norms
            prediction = self.clf.predict([features]) - 1
        else:
            features = self.extract_features(data)
            features = features / self.norms[channel_i]
            prediction = self.clf[channel_i].predict([features]) - 1
        return int(prediction)

    def classify_thresholds(self, channel_i, data):
        if channel_i == 'all':  # for the case of multi-channel decoding
            prediction = False
            channel_len = len(self.channel_decode_default)
            for i in range(channel_len):
                prediction = any(data[:, i] > self.stim_threshold[i])
                if prediction:
                    prediction = 1 << 0 | 1 << 1 | 1 << 2 | 1 << 3    # enable all channels
                    break
        else:
            prediction = data >= self.stim_threshold[channel_i]
            prediction = any(prediction)
        return int(prediction)

    def extract_features(self, data):
        feature_obj = Features(data, self.sampling_freq, self.features_id)
        features = feature_obj.extract_features()
        return features

    def update_on_off(self, data):
        if data[0] == 0xF8:
            if data[1] == 0xF8:
                self.odin_obj.send_start()
            elif data[1] == 100:
                self.real_channel_enable_flag = True
        elif data[0] == 0x8F:
            self.odin_obj.send_stop()
            self.real_channel_disable_flag = True
        print('updated on/off status...')
        print(data)

    def update_channel_enable(self, data):
        self.odin_obj.channel_enable = data[1]
        command = self.odin_obj.send_channel_enable()
        print('sending command to odin...')
        print(command)
        print('updated channel enable...')
        print(data)
        # time.sleep(0.04)

    def update_threshold_digit(self, data):
        address = {
            0xCC: 0,
            0xCD: 1,
            0xCE: 2,
            0xCF: 3
        }
        channel_id = address.get(data[0])
        self.stim_threshold_digit[channel_id] = data[1]
        self.update_threshold(channel_id)
        print('updated threshold digits...')
        print(data)
        print(self.stim_threshold)
        # time.sleep(0.04)

    def update_threshold_power(self, data):
        address = {
            0xD0: 0,
            0xD1: 1,
            0xD2: 2,
            0xD3: 3
        }
        channel_id = address.get(data[0])
        if data[1] > 50:
            self.stim_threshold_power[channel_id] = np.array(data[1] - 256, dtype=np.float)
        else:
            self.stim_threshold_power[channel_id] = data[1]
        self.update_threshold(channel_id)
        print('updated threshold power...')
        print(data)
        print(self.stim_threshold)
        # time.sleep(0.04)

    def update_threshold(self, channel_id):
        self.stim_threshold[channel_id] = self.stim_threshold_digit[channel_id] * 10 ** self.stim_threshold_power[channel_id]

    def update_threshold_upper(self, data):
        self.stim_threshold_upper = data[1]
        print('updated upper threshold...')
        print(data)
        # time.sleep(0.04)

    def update_threshold_lower(self, data):
        self.stim_threshold_lower = data[1]
        print('updated lower threshold...')
        print(data)
        # time.sleep(0.04)

    def update_debounce_delay(self, data):
        self.stim_debounce_delay = data[1]
        print('updated debounce delay...')
        print(data)
        # time.sleep(0.04)

    def update_step_size(self, data):
        self.odin_obj.step_size = data[1]
        print('updated step size...')
        print(data)
        # time.sleep(0.04)

    def update_frequency(self, data):
        self.odin_obj.frequency = data[1]
        self.odin_obj.send_frequency()
        print('updated frequency...')
        print(data)
        # time.sleep(0.04)

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
        # time.sleep(0.04)

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
        # time.sleep(0.04)

    def update_decoding_window_size(self, data):
        self.window_class = data[1] / 1000.  # gotten in milliseconds
        print('updated decoding window size...')
        print(data)

    def update_overlap_window_size(self, data):
        self.window_overlap = data[1] / 1000.  # gotten in milliseconds
        print('updated overlap window size...')
        print(data)

    def update_sampling_freq(self, data):
        self.sampling_freq = data[1]
        print('updated sampling frequency...')
        print(data)

    def update_hp_thresh(self, data):
        self.hp_thresh = data[1]

    def update_lp_thresh(self, data):
        self.lp_thresh = data[1]

    def update_notch_thresh(self, data):
        self.notch_thresh = data[1]

    def update_extend_stimulation(self, data):
        self.extend_stim_orig = data[1] / 1000.
        print('updated extend stimulation...')
        print(data)

    def update_classify_dimention(self, data):
        if not self.pin_sh_obj.input_GPIO():
            value = {
                9: True,
                10: False
            }
            self.flag_multi_channel = value.get(data[1])
            self.check_classify_dimension()
            print('updated classify dimensoin...')
            print(data)

    def update_classify_methods(self, data):
        if not self.pin_sh_obj.input_GPIO():
            value = {
                9: 'thresholds',
                10: 'features'
            }
            self.classify_method = value.get(data[1])
            self.classify_function = self.method_classify_all.get(self.classify_method)
            print('updated classify method to %s...' % value.get(data[1]))
            print(data)

    def update_closed_loop(self, data):
        if not self.pin_sh_obj.input_GPIO():
            self.check_closed_loop()
            print('updated closed loop...')
            print(data)

    def update_reset_flag(self, data):
        if not self.pin_sh_obj.input_GPIO():
            self.check_reset_flag()
            print('updated flag reset...')
            print(data)

    def update_stimulation_flag(self, data):
        if not self.pin_sh_obj.input_GPIO():
            value = {
                8: True,
                9: False
            }
            self.start_integration_flag = value.get(data[1])
            self.check_stimulation_flag()
            print('updated stimulation flag...')
            print(data)

    def update_saving_flag(self, data):
        if not self.pin_sh_obj.input_GPIO():
            value = {
                8: False,
                9: True
            }
            self.flag_save_new = value.get(data[1])
            self.check_saving_flag()
            print('updated saving flag...')
            print(data)

    def update_saving_transfer(self, data):
        files = glob.glob('/home/pi/Data/*.csv')
        for x in files:
            try:
                os.remove(x)
            except OSError:
                print("Error while deleting file: %s" % x)
        print('removed recorded files...')

    def update_stimulation_pattern(self, data):
        if not self.pin_sh_obj.input_GPIO():
            temp = data[1] - 520
            self.stim_pattern_input.append(temp & 0xF)
            self.stim_pattern_output.append(temp >> 4)
            print('stim pattern input: ')
            print(self.stim_pattern_input)
            print('stim pattern output: ')
            print(self.stim_pattern_output)
            print('updated stim pattern...')
            print(data)
            self.flag_save_input_output = True  # save pattern in saving file

    def update_stimulation_pattern_flag(self, data):
        if not self.pin_sh_obj.input_GPIO():
            self.stim_pattern_input = []
            self.stim_pattern_output = []
            print('cleared stim pattern...')
            print(data)

    def change_channel_enable(self):
        prediction = self.check_stim_pattern()  # check the stimulation pattern to manipulate the stimulating channels

        self.odin_obj.channel_enable = prediction
        command = self.odin_obj.send_channel_enable()
        print('sending command to odin...')
        print(command)
        return command

    def check_extend_stim(self, prediction):
        for i, x in enumerate(self.prediction_changed_flag):
            if prediction >> i & 1:
                self.extend_stim_flag[i] = True
                self.extend_stim[i] = self.extend_stim_orig
            elif x and not (prediction >> i & 1) and self.extend_stim_flag[i]:
                if self.extend_stim[i] > 0:
                    self.prediction_changed_flag[i] = False
                    self.extend_stim[i] -= float(self.size_temp) / self.sampling_freq
                    print('masked channel %d, remaining waiting time: %.3f' % (i+1, self.extend_stim[i]))
                else:
                    self.extend_stim_flag[i] = False
                    self.extend_stim[i] = self.extend_stim_orig

    def check_change_parameter(self):
        # if self.change_parameter_event.is_set():
        while not self.change_parameter_queue.empty():
            try:
                data_parameter = self.change_parameter_queue.get()
                # print(data_parameter)
                self.address.get(data_parameter[0])(data_parameter)
                # self.change_parameter_event.clear()
            except TypeError:
                print('failed to update the command:')
                print(data_parameter)

    def check_classify_method(self):
        start_flag = not self.flag_classify_method
        stop_flag = self.flag_classify_method
        if self.pin_sh_obj.input_GPIO():
            start_flag = start_flag and self.pin_classify_method_obj.input_GPIO()
            stop_flag = stop_flag and not self.pin_classify_method_obj.input_GPIO()

        if start_flag:  # switch to feature extraction
            self.flag_classify_method = True
            self.classify_function = self.method_classify_all.get('features')
            time.sleep(0.1)
            print('switched to feature classification mode...')

        if stop_flag:  # swithc to thresholding classification
            self.flag_classify_method = False
            self.classify_function = self.method_classify_all.get('thresholds')
            time.sleep(0.1)
            print('switched to thresholding classification mode...')

    def check_closed_loop(self):
        start_flag = not self.flag_closed_loop
        stop_flag = self.flag_closed_loop
        if self.pin_sh_obj.input_GPIO():
            start_flag = start_flag and not self.pin_closed_loop_obj.input_GPIO()
            stop_flag = stop_flag and self.pin_closed_loop_obj.input_GPIO()

        if start_flag:
            self.flag_closed_loop = True
            if not np.array(self.odin_obj.channel_enable).all():
                self.odin_obj.channel_enable = 1 << 0 | 1 << 1 | 1 << 2 | 1 << 3    # enable all channels after toggling to closed-loop mode
                self.odin_obj.send_channel_enable()
            print('switched to closed-loop mode...')
            time.sleep(0.1)

        if stop_flag:
            self.flag_closed_loop = False
            print('switched to single stimulation mode...')
            time.sleep(0.1)

    def check_classify_dimension(self):
        start_flag = not self.flag_multi_channel
        stop_flag = self.flag_multi_channel
        if self.pin_sh_obj.input_GPIO():
            start_flag = start_flag and self.pin_sm_channel_obj.input_GPIO()
            stop_flag = stop_flag and not self.pin_sm_channel_obj.input_GPIO()

        if start_flag:  # switch to multi-channel classification
            self.flag_multi_channel = True
            time.sleep(0.1)
            self.load_classifier()
            print('switched to multi-channel classification mode...')

        if stop_flag:  # switch to single-channel classification
            self.flag_multi_channel = False
            time.sleep(0.1)
            self.load_classifier()
            print('switch to single-channel classification mode...')

    def check_reset_flag(self):
        start_flag = not self.flag_reset
        stop_flag = self.flag_reset
        if self.pin_sh_obj.input_GPIO():
            start_flag = start_flag and self.pin_reset_obj.input_GPIO()
            stop_flag = stop_flag and not self.pin_reset_obj.input_GPIO()
        if start_flag:  # reload parameters
            self.flag_reset = True
            # self.thresholds = np.genfromtxt('thresholds.txt', delimiter=',', defaultfmt='%f')
            self.odin_obj.get_coefficients()
            self.odin_obj.send_parameters()
            time.sleep(0.04)
            self.change_channel_enable()
            # print('thresholds have been reset...')
            # print(self.thresholds)
            time.sleep(0.1)

        if stop_flag:
            self.flag_reset = False
            print('reset flag changed to False...')
            time.sleep(0.1)

    def check_stimulation_flag(self):
        start_flag = not self.start_integration_flag
        stop_flag = self.start_integration_flag
        if self.pin_sh_obj.input_GPIO():  # hardware
            start_flag = start_flag and self.pin_stim_obj.input_GPIO()
            stop_flag = stop_flag and not self.pin_stim_obj.input_GPIO()

        if start_flag:  # send starting sequence to stimulator
            print('started stimulation...')
            self.start_integration_flag = True  # start the stimulation
            self.start_stimulation_initial = True  # to insert initial flag in saved file
            self.odin_obj.send_start_sequence()  # send start bit to odin
            self.change_channel_enable()  # send a channel enable that is the current prediction

        if stop_flag:  # send ending sequence to setimulator
            print('stopped stimulation...')
            self.start_integration_flag = False
            self.stop_stimulation_initial = True
            amp_temp = self.odin_obj.amplitude
            self.odin_obj.send_stop_sequence()  # send stop bit to odin
            self.odin_obj.amplitude = amp_temp

    def check_saving_flag(self):
        stop_flag = not self.flag_save_new
        start_flag = self.flag_save_new
        if self.pin_sh_obj.input_GPIO():  # hardware
            stop_flag = stop_flag and self.pin_save_obj.input_GPIO()
            start_flag = start_flag and not self.pin_save_obj.input_GPIO()

        if stop_flag:  # start a new file to save
            self.flag_save_new = True
            print('stop saving...')
            time.sleep(0.1)

        if start_flag:
            self.flag_save_new = False
            command_array = np.zeros([1, np.size(self.data, 1)])  # create an empty command array
            command_array[0, 0] = self.flag_multi_channel
            command_array[0, 1] = self.flag_classify_method
            command_array[0, 2] = self.window_class
            command_array[0, 3] = self.window_overlap
            command_array[0, 4] = self.sampling_freq
            command_array[0, 5] = self.extend_stim_orig
            command_array[0, 6] = self.hp_thresh
            command_array[0, 7] = self.lp_thresh
            command_array[0, 8] = self.notch_thresh
            self.saving_file = Saving()
            self.saving_file.save(command_array, "a")  # save the counter and the command
            self.flag_save_input_output = True
            print('resume saving with a new file...')
            time.sleep(0.1)

    def check_filename(self):
        if not self.filename_queue.empty():
            filename = self.filename_queue.get()
            if filename == 'DISCARDFILE!!!':
                os.remove(self.saving_file.saving_full_filename)
                print("removed %s..." + self.saving_file.saving_full_filename)
            elif filename == 'GIMMENUMCLASS!!!':  # triggered when the "update movement" button is pressed
                self.load_classifier()
                self.num_class_value.value = self.num_class
            else:
                filename_full = os.path.join("Data", filename) + ".csv"
                print("saved file %s..." % filename_full)
                os.rename(self.saving_file.saving_full_filename, filename_full)

    def check_stim_pattern(self):
        if self.stim_pattern_input:  # check if and only if self.stim_pattern is not empty
            if self.prediction in self.stim_pattern_input:
                return self.stim_pattern_output[self.stim_pattern_input.index(self.prediction)]
            else:
                return self.odin_obj.channel_enable
        else:
            return self.prediction

    def _get_window_class_sample_len(self):
        return int(self.window_class * self.sampling_freq)

    def _get_window_overlap_sample_len(self):
        return int(self.window_overlap * self.sampling_freq)


