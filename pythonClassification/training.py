import numpy as np
import pickle
from sklearn.svm import SVC
import burst_detection
from sklearn import preprocessing
import os
import sys


class Training():
    def __init__(self, sampling_freq, point_start, point_end):
        self.data_location = os.path.join("Data", "Training")

        self.sampling_freq = sampling_freq
        self.point_start = point_start
        self.point_end = point_end

        self.data = []
        self.data_TKEO = []

        self.burst_loc_start = []

    def load_data(self):
        self.data = [np.genfromtxt(os.path.join(self.data_location, x), delimiter=',', defaultfmt='%f')
                     for x in os.listdir(self.data_location)]

    def convert_TKEO(self, data):
        self.data_TKEO = [burst_detection.convert_TKEO(x, self.sampling_freq) for x in data]

    def detect_burst(self, multiplier):
        result_threshold = burst_detection.moving_window_threhsolding(self.data_TKEO[0])  # first file is baseline
        baseline_std = result_threshold.get('baseline_std')
        threhosld = multiplier * baseline_std





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
