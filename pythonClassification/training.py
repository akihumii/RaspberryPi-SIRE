import numpy as np
import pickle
from sklearn.svm import SVC
import burst_detection
from sklearn import preprocessing
import os
from features import Features
from filtering import Filtering
import sys


class Training(Features, Filtering):
    def __init__(self, channel_decode, sampling_freq, point_start, point_end, features_id, hp_thresh, lp_thresh, notch_thresh, thresh_multiplier, fix_window_size=0):
        Features.__init__(self, sampling_freq, features_id)
        Filtering.__init__(self, sampling_freq, hp_thresh, lp_thresh, notch_thresh, persistent_memory=False)

        self.data_location = os.path.join("Data", "Training")

        self.sampling_freq = sampling_freq
        self.point_start = point_start
        self.point_end = point_end

        self.fix_window_size = fix_window_size * self.sampling_freq # in seconds

        self.thresh_multiplier = thresh_multiplier
        self.min_distance = 0.02 * sampling_freq

        self.channel_decode = channel_decode

        self.moving_window_lag = 1250
        self.moving_window_threshold = 2.5
        self.moving_window_influence = 0

        self.data_raw = []
        self.data_TKEO = []

        self.locs_starting_point_all = []  # combine detected burst location in all channels into one set
        self.locs_end_point_all = []

        self.bursts = []

        self.features = []
        self.classes = []
        self.features_all = []

    def train_classifier(self):  # run the whole set of codes :)
        self.load_data()
        self.convert_TKEO(self.data_raw)
        self.detect_burst_loc(self.data_TKEO[0], self.data_TKEO[1:], self.thresh_multiplier)  # first file is baseline

        data_filtered = [self.filter(x) for x in self.data_raw[1:]]
        self.get_burst(data_filtered)
        self.get_features(data_filtered)

        classifiers = train_classifier_SVC(np.array(self.features_all), self.classes)
        return classifiers

    def load_data(self):
        self.data_raw = [np.array(np.genfromtxt(os.path.join(self.data_location, x), delimiter=',', defaultfmt='%f'))[:, self.channel_decode]
                         for x in os.listdir(self.data_location)]

    def convert_TKEO(self, data):
        for x in data:
            data_TKEO_temp = np.hstack([burst_detection.convert_TKEO(x[:, y], self.sampling_freq) for y in range(np.size(x, 1))])
            self.data_TKEO.append(data_TKEO_temp)
        # self.data_TKEO = [burst_detection.convert_TKEO(x, self.sampling_freq) for x in data]

    def detect_burst_loc(self, data_baseline, data, multiplier):
        num_channel = np.size(data_baseline, 1)
        baseline_std = [burst_detection.moving_window_threhsolding(
            data_baseline[:, i], self.moving_window_lag, self.moving_window_threshold, self.moving_window_influence).get('baseline_std')
                        for i in range(num_channel)]
        threshold = multiplier * np.array(baseline_std)  # get the threshold to use in TKEO

        locs_starting_point = [[] for __ in data]  # an array for each data
        locs_end_point = [[] for __ in data]

        for i, x in enumerate(data):
            data_len = np.size(x, 0)
            locs_starting_point_temp = [burst_detection.trigger(x[:, j], threshold[j], point_start=self.point_start, min_distance=self.min_distance)
                                        for j in range(num_channel)]
            # locs_end_point_temp = [burst_detection.find_trigger_end_point(x[:, i], threshold[i], locs_starting_point_temp[i], self.point_end).get('locs')
            #                        for i in range(num_channel)]

            if self.fix_window_size:  # use the fixed burst length as the end of the bursts
                for j in range(num_channel):
                    [locs_starting_point_temp, locs_end_point_temp] = \
                        burst_detection.edit_burst_length(data_len, self.fix_window_size, locs_starting_point_temp[j])
                    locs_starting_point[i].append(locs_starting_point_temp)  # multiple array for channels in each data
                    locs_end_point[i].append(locs_end_point_temp)

            [locs_starting_point_all_temp, locs_end_point_all_temp] = \
                burst_detection.merge_channel_burst(locs_starting_point[i], locs_end_point[i])

            self.locs_starting_point_all = np.append(self.locs_starting_point_all, locs_starting_point_all_temp)
            self.locs_end_point_all = np.append(self.locs_end_point_all, locs_end_point_all_temp)

            # values_starting_point[i] = x[locs_starting_point_all, :]
            # values_end_point[i] = x[locs_end_point_all, :]

    def get_burst(self, data):
        self.bursts = [burst_detection.get_bursts_point(x, self.locs_starting_point_all[i], self.locs_end_point_all[i])
                       for i, x in enumerate(data)]

        self.features = [[] for __ in data]

    def get_features(self, data):
        for i, x in enumerate(data):  # different movement
            num_bursts = len(x)
            num_channel = np.size(x[0], 1)
            for j in range(num_bursts):  # different bursts
                self.features[i] = np.append(np.hstack(self.features[i],
                                                       [self.extract_features(x[j, k]) for k in range(num_channel)]))
            self.classes[i] = np.vstack(i * np.ones(num_bursts))

        self.features_all = np.vstack(self.features)
        self.classes = np.vstack(self.classes)


def train_classifier_SVC(features, classes):
    norms = np.mean(features, axis=0)
    features_normalized = features / norms
    gamma_value = 1. / (np.size(features_normalized, 1) * features_normalized.std())
    clf = SVC(kernel='poly', C=50.0, gamma=gamma_value)
    classifiers = clf.fit(features_normalized, classes)

    return classifiers


def train(target_dir):
    print("started...")
    # cwd = os.getcwd()
    # target_dir = os.path.join(cwd, 'classificationTmp')

    print("processing the folder %s " % target_dir)

    if os.path.exists(target_dir):
        file_feature = [f for f in os.listdir(target_dir) if f.startswith('featuresCh')]

        file_class = [f for f in os.listdir(target_dir) if f.startswith('classCh')]

        for i in range(len(file_class)):
            # get features and classes from csv files
            features_tmp = np.genfromtxt(os.path.join(target_dir, file_feature[i]), delimiter=',', defaultfmt='%f')
            class_tmp = np.genfromtxt(os.path.join(target_dir, file_class[i]), delimiter=',', defaultfmt='%f')

            # normalize features
            # features_normalized = features_tmp
            # [features_normalized, norms] = preprocessing.normalize(features_tmp, norm='max', axis=0, return_norm=True)
            norms = np.mean(features_tmp, axis=0)
            features_normalized = features_tmp / norms
            # norms = preprocessing.MinMaxScaler().fit(features_tmp)
            # features_normalized = norms.transform(features_tmp)

            print('fitting %s' % file_feature[i])

            # training SVC
            gamma_value = 1./(np.size(features_normalized, 1)*features_normalized.std())
            clf = SVC(kernel='poly', C=50.0, gamma=gamma_value)
            classifiers = clf.fit(features_normalized, class_tmp)

            # saving classifiers and norms
            filename = 'classifierCh%s.sav' % file_feature[i][file_feature[i].find('Ch')+2]
            filename_norms = 'normsCh%s.csv' % file_feature[i][file_feature[i].find('Ch') + 2]
            # filename_norms = 'normsCh%s.sav' % file_feature[i][file_feature[i].find('Ch')+2]

            pickle.dump(classifiers, open(os.path.join(target_dir, filename), 'wb'))
            np.savetxt(os.path.join(target_dir, filename_norms), norms, delimiter=',')
            # pickle.dump(norms, open(os.path.join(target_dir, filename_norms), 'wb'))

            print("%s%d has been saved..." % (os.path.join(target_dir, filename), i))
            print("%s%d has been saved..." % (os.path.join(target_dir, filename_norms), i))
    else:
        print("no %s is found..." % target_dir)

    print("done...")


if __name__ == "__main__":
    train('C:\\Users\\lsitsai\\Desktop\\Marshal\\20190131_Chronic_NHP_wireless_implant_Alvin\\Info\\classificationTmp')
    # train('C:\\Users\\lsitsai\\Desktop\\Marshal\\20190131_Chronic_NHP_wireless_implant_Alvin\\Info\\classificationTmp\\storage\\normalized')
    # train(str(sys.argv[1]))
