import numpy as np
import pickle
from sklearn.svm import SVC
from sklearn import preprocessing
import os
import sys


def train_full(file_feature, file_class):
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
    num_bursts = [len(np.where(classes == x)[0]) for x in num_classes_type]
    num_bursts_min = min(num_bursts)
    target_locs = np.hstack([type_switch_func.get(type_switch)(np.where(classes == x)[0], training_ratio, num_bursts_min) for i, x in enumerate(num_classes_type)])

    target_features = features[target_locs, :]
    target_classes = classes[target_locs]

    return [target_features, target_classes]


def get_training_locs(classes_each, training_ratio, num_bursts_min):
    np.random.shuffle(classes_each)
    # num_item = len(classes_each)
    return classes_each[0: int(num_bursts_min * training_ratio)]


def get_testing_locs(classes_each, training_ratio, num_bursts_min):
    np.random.shuffle(classes_each)
    # num_item = len(classes_each)
    return classes_each[int(num_bursts_min * training_ratio)+1: num_bursts_min-1]


if __name__ == "__main__":
    # train('F:\\Derek_Desktop_Backup\\Marshal\\20190131_Chronic_NHP_wireless_implant_Alvin\\Info\\classificationTmp\\visualization')
    # train('C:\\Users\\lsitsai\\Desktop\\Marshal\\20190131_Chronic_NHP_wireless_implant_Alvin\\Info\\classificationTmp\\storage\\normalized')
    # train(str(sys.argv[1]))
    train_full(str(sys.argv[1]), str(sys.argv[2]))