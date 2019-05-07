import numpy as np
import pickle
from sklearn.svm import SVC
from sklearn import preprocessing
import os
import sys


def train(file_feature, file_class):
    print("started...")

    print("processing feature %s " % file_feature)

    if os.path.exists(file_feature):
        # get features and classes from csv files
        features_tmp = np.genfromtxt(file_feature, delimiter=',', defaultfmt='%f')
        class_tmp = np.genfromtxt(file_class, delimiter=',', defaultfmt='%f')

        # normalize features
        # features_normalized = features_tmp
        # [features_normalized, norms] = preprocessing.normalize(features_tmp, norm='max', axis=0, return_norm=True)
        norms = np.mean(features_tmp, axis=0)
        features_normalized = features_tmp / norms
        # norms = preprocessing.MinMaxScaler().fit(features_tmp)
        # features_normalized = norms.transform(features_tmp)

        print('fitting %s' % file_feature)

        # training SVC
        gamma_value = 1./(np.size(features_normalized, 1)*features_normalized.std())
        clf = SVC(kernel='poly', C=50.0, gamma=gamma_value)
        classifiers = clf.fit(features_normalized, class_tmp)

        file_dir = os.path.dirname(file_feature)
        file_base = os.path.basename(file_feature)

        # saving classifiers and norms
        i_ch = 10  # index of channel number
        file_classifier = 'classifierCh%s.sav' % file_base[i_ch]
        file_norms = 'normsCh%s.csv' % file_base[i_ch]
        # file_norms = 'normsCh%s.sav' % file_feature[i][file_feature[i].find('Ch')+2]

        pickle.dump(classifiers, open(os.path.join(file_dir, file_classifier), 'wb'))
        np.savetxt(os.path.join(file_dir, file_norms), norms, delimiter=',')
        # pickle.dump(norms, open(os.path.join(target_dir, file_norms), 'wb'))

        print("%s has been saved..." % os.path.join(file_dir, file_classifier))
        print("%s has been saved..." % os.path.join(file_dir, file_norms))
    else:
        print("no %s is found..." % file_feature)

    print("done...")


if __name__ == "__main__":
    # train('C:\\Users\\lsitsai\\Desktop\\Marshal\\20190131_Chronic_NHP_wireless_implant_Alvin\\Info\\classificationTmp')
    # train('C:\\Users\\lsitsai\\Desktop\\Marshal\\20190131_Chronic_NHP_wireless_implant_Alvin\\Info\\classificationTmp\\storage\\normalized')
    # train(str(sys.argv[1]), str(sys.argv[2]))
    train('featuresCh4_data_20190131_134012_20190507122133_20190507122144.csv',
          'classCh4_data_20190131_134012_20190507122133_20190507122144.csv')
