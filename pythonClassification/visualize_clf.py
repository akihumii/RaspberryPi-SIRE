import numpy as np
import matplotlib.pyplot as plt
import pickle
import os
import classification_training
import pandas as pd
import seaborn as sns
from sklearn.manifold import TSNE


def predict_features(clf, features, classes=[]):
    classes_unique = np.unique(classes)
    classes_predicted = clf.predict(features)
    if len(classes):
        classes = np.hstack(classes)
        checking_table = [np.array(classes_predicted[np.where(classes == x)]) == np.array(classes[np.where(classes == x)]) for x in classes_unique]
        performance = [np.array(sum(x)).astype(float) / len(x) for x in checking_table]
        return performance

    else:
        return classes_predicted


def get_file_info(target_dir, flag_single_channel):
    if flag_single_channel:
        file_feature = sorted(f for f in os.listdir(target_dir) if f.startswith('features') and 'featuresCha' not in f)
        file_class = sorted(f for f in os.listdir(target_dir) if f.startswith('class') and 'classCha' not in f)
        file_norms = sorted(f for f in os.listdir(target_dir) if f.startswith('norms') and 'normsCha' not in f)
        file_clf = sorted(f for f in os.listdir(target_dir) if f.startswith('classifier') and 'classifierCha' not in f)
    else:
        file_feature = sorted(f for f in os.listdir(target_dir) if f.startswith('features') and 'featuresCha' in f)
        file_class = sorted(f for f in os.listdir(target_dir) if f.startswith('class') and 'classCha' in f)
        file_norms = sorted(f for f in os.listdir(target_dir) if f.startswith('norms') and 'normsCha' in f)
        file_clf = sorted(f for f in os.listdir(target_dir) if f.startswith('classifier') and 'classifierCha' in f)

    return dict(file_feature=file_feature,
                file_class=file_class,
                file_norms=file_norms,
                file_clf=file_clf)


def visualize_features(plot_flag, target_dir, flag_single_channel):
    file_info = get_file_info(target_dir, flag_single_channel)
    num_file = len(file_info.get('file_feature'))

    prediction = [[] for __ in range(num_file)]

    for i in range(num_file):
        # load classifier
        clf = pickle.load(open(os.path.join(target_dir, file_info.get('file_clf')[i]), 'rb'))

        # load features
        features = np.genfromtxt(os.path.join(target_dir, file_info.get('file_feature')[i]), delimiter=',', defaultfmt='%f')

        # load classes
        classes = np.genfromtxt(os.path.join(target_dir, file_info.get('file_class')[i]), delimiter=',', defaultfmt='%f')

        # load norms
        norms = np.genfromtxt(os.path.join(target_dir, file_info.get('file_norms')[i]), delimiter=',')
        # norms = pickle.load(open(os.path.join(target_dir, file_norms[i]), 'rb'))

        # normalize the features
        # features_normalized = features
        features_normalized = features / norms
        # features_normalized = norms.transform(features)

        # get the testing set
        if flag_single_channel:
            training_ratio = 0.7
            [features_testing, classes_testing] = classification_training.get_partial_set(features_normalized, classes, training_ratio, 'testing')

            # classify
            prediction[i] = predict_features(clf, features_testing, classes_testing)

            if plot_flag:
                plt.figure(i)
                plot_scatter(features_testing, classes_testing, features_normalized, clf, file_info.get('file_class')[i])
        else:
            if flag_hide_coconcentrate:
                [features_normalized, classes] = hide_class(features_normalized, classes, 4)
            features_result = get_data_TSNE(features_normalized, classes)
            if plot_flag:
                plot_TSNE(features_result)

    if plot_flag:
        plt.show()

    return prediction


def hide_class(features_normalized, classes, target_class):
    locs = np.where(classes == target_class)
    classes = np.delete(classes, locs, 0)
    features_normalized = np.delete(features_normalized, locs, 0)
    return features_normalized, classes


def get_data_TSNE(features_normalized, classes):
    print('computing TSNE...')
    features_embedded = TSNE(init='random', random_state=0, perplexity=30).fit_transform(features_normalized)
    label_all = ["baseline", "biceps", "triceps", "co-contraction"]
    label = np.vstack([label_all[int(x) - 1] for x in classes])
    features_result = np.hstack([features_embedded, np.vstack(classes.astype(int))])
    features_result = pd.DataFrame(data=features_result, columns=['DIM1', 'DIM2', 'classes'])
    features_result['label'] = label

    return features_result


def plot_TSNE(features_result):
    print("prepare to do scatter plot...")
    sns.set_context("notebook", font_scale=1.1)
    sns.set_style("ticks")
    sns.scatterplot(x='DIM1', y='DIM2', hue='label', data=features_result,
                    style='label', palette='Set1', alpha=0.4)
    plt.title('t-SNE Results')
    print("done the plotting...")


def plot_scatter(features_testing, classes_testing, features_normalized, clf, file_class):
    plt.clf()

    # plt.scatter(clf.support_vectors_[:, 0], clf.support_vectors_[:, 1], s=80,
    #             facecolors='none', zorder=10, edgecolors='k')
    num_testing = np.size(features_testing, 0)
    plt.scatter(features_testing[:, 0], features_testing[:, 1], c=classes_testing, zorder=10, cmap=plt.cm.Paired,
                edgecolors='k')
    plt.legend([str(num_testing)])
    plt.axis('tight')
    x_min = min(features_normalized[:, 0])
    x_max = max(features_normalized[:, 0])
    y_min = min(features_normalized[:, 1])
    y_max = max(features_normalized[:, 1])

    XX, YY = np.mgrid[x_min:x_max:200j, y_min:y_max:200j]
    Z = clf.decision_function(np.c_[XX.ravel(), YY.ravel()])

    # Put the result into a color plot
    Z = Z.reshape(XX.shape)
    plt.pcolormesh(XX, YY, Z > 0, cmap=plt.cm.Paired)
    plt.contour(XX, YY, Z, colors=['k', 'k', 'k'], linestyles=['--', '-', '--'],
                levels=[-.5, 0, .5])

    plt.xlim(x_min, x_max)
    plt.ylim(y_min, y_max)

    # axes labels
    label_x = 'meanValue'
    label_y = 'numSignChanges'
    label_title = file_class

    plt.xlabel(label_x)
    plt.ylabel(label_y)
    plt.title(label_title)


def multiple_prediction(num_repetition, target_dir, plot_flag, flag_single_channel):
    prediction_all = []
    for i in range(num_repetition):
        print('processing loop %d:' % i)
        classification_training.train(target_dir)
        prediction = visualize_features(plot_flag, target_dir, flag_single_channel)
        prediction_all.append(prediction)

    prediction_all = np.array(prediction_all)
    prediction_mean = np.mean(prediction_all, 0)
    prediction_median = np.percentile(prediction_all, 50, 0)
    prediction_5_perc = np.percentile(prediction_all, 5, 0)
    prediction_95_perc = np.percentile(prediction_all, 95, 0)

    return dict(prediction_all=prediction_all,
                prediction_mean=prediction_mean,
                prediction_median=prediction_median,
                prediction_5_perc=prediction_5_perc,
                prediction_95_perc=prediction_95_perc)


if __name__ == "__main__":
    # target_dir = 'F:\\Derek_Desktop_Backup\\Marshal\\20190131_Chronic_NHP_wireless_implant_Alvin\\Info\\classificationTmp\\visualization'
    # target_dir = 'C:\\Data\\Info\\classificationTmp\\Visualize'
    # target_dir = 'C:\\Data\\Info\\classificationTmp'
    # target_dir = 'F:\\Derek_Desktop_Backup\\Marshal\\20190626_Chronic_NHP_wireless_implant_Alvin\\Info\\classificationTmp\\Visualize'
    # target_dir = 'F:\\Derek_Desktop_Backup\\Marshal\classifierImrpovement\\Info_20190802data_settings_60_30\\classificationTmp'
    # target_dir = 'F:\\Derek_Desktop_Backup\\Marshal\\classifierImrpovement\\Info_20190802_old_model\\classificationTmp'
    # target_dir = 'F:\\Derek_Desktop_Backup\\Marshal\\classifierImrpovement\\Info_20190802_old_model\\classificationTmp'
    target_dir = 'F:\\Derek_Desktop_Backup\\Marshal\\20190808_Chronic_NHP_Alvin\\testing\\Info\\classificationTmp'
    # target_dir = 'C:\\Users\\lsitsai\\Desktop\\Marshal\\20190131_Chronic_NHP_wireless_implant_Alvin\\Info\\classificationTmp\\storage\\normalized'
    plot_flag = True
    # flag_single_channel = True
    flag_single_channel = False
    flag_hide_coconcentrate = True
    # flag_hide_coconcentrate = False
    num_repeatition = 1
    prediction_output = multiple_prediction(num_repeatition, target_dir, plot_flag, flag_single_channel)
    print('median: ')
    print(prediction_output.get('prediction_median'))
    print('5 perc: ')
    print(prediction_output.get('prediction_5_perc'))
    print('95 perc: ')
    print(prediction_output.get('prediction_95_perc'))

