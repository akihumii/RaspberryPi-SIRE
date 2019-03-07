import numpy as np
import pickle
from sklearn.svm import SVC
import os
import sys


def train(target_file):
    print("started...")
    # cwd = os.getcwd()
    # target_dir = os.path.join(cwd, 'classificationTmp')
    target_dir = target_file

    print("processing the folder %s " % target_file)

    if os.path.exists(target_dir):
        file_feature = [f for f in os.listdir(target_dir) if f.startswith('featuresCh')]

        file_class = [f for f in os.listdir(target_dir) if f.startswith('classCh')]

        for i in range(len(file_class)):
            features_tmp = np.genfromtxt(os.path.join(target_dir, file_feature[i]), delimiter=',', defaultfmt='%f')
            
            class_tmp = np.genfromtxt(os.path.join(target_dir, file_class[i]), delimiter=',', defaultfmt='%f')

            print('fitting %s' % file_feature[i])

            gamma_value = 1./(np.size(features_tmp, 1)*features_tmp.std())

            clf = SVC(kernel='poly', gamma=gamma_value)

            classifiers = clf.fit(features_tmp, class_tmp)

            filename = 'classifierCh%s.sav' % file_feature[i][file_feature[i].find('Ch')+2]

            pickle.dump(classifiers, open(os.path.join(target_dir, filename), 'wb'))
            print("%s%d has been saved..." % (os.path.join(target_dir, filename), i))

    else:
        print("no %s is found..." % target_dir)

    print("done...")


if __name__ == "__main__":
    # train('C:\\Users\\lsitsai\\Desktop\\Marshal\\20190131_Chronic_NHP_wireless_implant_Alvin\\Info\\classificationTmp')
    train(str(sys.argv[1]))
