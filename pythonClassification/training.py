import numpy as np
import pickle
from sklearn.svm import SVC
import os
import sys


class Training:
    def __init__(self):
        print("started...")
        cwd = os.getcwd()
        self.target_dir = os.path.join(cwd, 'classificationTmp')
        self.file_feature = []
        self.file_class = []
        self.clf = None

    def create_classifier(self, target_file):
        self.file_feature = [f for f in os.listdir(self.target_dir)
                             if f.startswith('featuresCh') and target_file in f]

        self.file_class = [f for f in os.listdir(self.target_dir)
                           if f.startswith('classCh') and target_file in f]

        self.clf = SVC(kernel='poly', degree=3, gamma='auto')

    def train(self):
            for i in range(len(self.file_class)):
                features_tmp = np.genfromtxt(os.path.join(self.target_dir, self.file_feature[i]), delimiter=',')

                class_tmp = np.genfromtxt(os.path.join(self.target_dir, self.file_class[i]), delimiter=',')

                classifiers = self.clf.fit(features_tmp.astype(np.float), class_tmp.astype(np.float))

                filename = 'classifierCh%s.sav' % self.file_feature[i][self.file_feature[i].find('Ch')+2]

                pickle.dump(classifiers, open(os.path.join(self.target_dir, filename), 'wb'))
                print("%s%d has been saved..." % (os.path.join(self.target_dir, filename), i))


if __name__ == "__main__":
    classifier = Training()
    
    if os.path.exists(classifier.target_dir):
        classifier.create_classifier(str(sys.argv[1]))
        classifier.train()
    else:
        print("no %s is found..." % classifier.target_dir)

    print("done...")
