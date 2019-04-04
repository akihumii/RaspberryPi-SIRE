import numpy as np
import pickle
from sklearn.svm import SVC
from sklearn import preprocessing
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
            # get features and classes from csv files
            features_tmp = np.genfromtxt(os.path.join(target_dir, file_feature[i]), delimiter=',', defaultfmt='%f')
            class_tmp = np.genfromtxt(os.path.join(target_dir, file_class[i]), delimiter=',', defaultfmt='%f')

            # select training set
            training_ratio = 0.7
            [features_tmp, class_tmp] = get_partial_set(features_tmp, class_tmp, training_ratio, 'training')

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


def get_partial_set(features, classes, training_ratio, type_switch):
    type_switch_func = {
        'training': get_training_locs,
        'testing': get_testing_locs,
    }

    num_classes_type = np.unique(classes)
    target_locs = np.hstack([type_switch_func.get(type_switch)(np.where(classes == x)[0], training_ratio) for i, x in enumerate(num_classes_type)])

    target_features = features[target_locs, :]
    target_classes = classes[target_locs]

    return [target_features, target_classes]


def get_training_locs(classes_each, training_ratio):
    np.random.shuffle(classes_each)
    num_item = len(classes_each)
    return classes_each[0: int(num_item * training_ratio)]


def get_testing_locs(classes_each, training_ratio):
    np.random.shuffle(classes_each)
    num_item = len(classes_each)
    return classes_each[int(num_item * training_ratio)+1: num_item-1]


if __name__ == "__main__":
    train('F:\\Derek_Desktop_Backup\\Marshal\\20190131_Chronic_NHP_wireless_implant_Alvin\\Info\\classificationTmp')
    # train('C:\\Users\\lsitsai\\Desktop\\Marshal\\20190131_Chronic_NHP_wireless_implant_Alvin\\Info\\classificationTmp\\storage\\normalized')
    # train(str(sys.argv[1]))
