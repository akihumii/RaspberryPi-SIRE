import ConfigParser
import numpy as np
import pickle
from features import Features
import matplotlib.pyplot as plt
from Tkinter import Tk
import tkinter.filedialog
import os


def extract_features(data, sampling_freq, features_id):
    feature_obj = Features(data, sampling_freq, features_id)
    return feature_obj.extract_features()


def get_window_features(data_channel, window_size_sample_unit, overlapping_size_sample_unit):
    step_array = range(0, np.size(data_channel, 0) - window_size_sample_unit, overlapping_size_sample_unit)
    features = np.array([extract_features(data_channel[step_array[j]:step_array[j] + window_size_sample_unit, i],
                                          sampling_freq, features_id)
                         for j in range(len(step_array))
                         for i in range(np.size(data_channel, 1))])
    features = np.hstack([features[:, i].reshape(-1, 4) for i in range(np.size(features, 1))])

    return features


def get_prediction_all(clf, features, overlapping_size_sample_unit, length_data):
    output = np.zeros([1, length_data])[0]
    step_array = np.arange(0, length_data, overlapping_size_sample_unit)
    for i in range(np.size(features, 0)):
        output[step_array[i]: (step_array[i+1])] = clf.predict([features[i, :]])
    output[step_array[np.size(features, 0)+1:]] = clf.predict([features[-1, :]])

    return output


def get_save_filename(titletext="Save as", config=None, filenamedefault=''):
    Tk().withdraw()
    initial_dir = get_initial_dir(config)
    filename = tkinter.filedialog.asksaveasfilename(title=titletext, initialdir=initial_dir, initialfile=filenamedefault,
                                                    filetypes=(("csv files", "*.csv"), ("all files", "*.*")))
    set_initial_dir(config, os.path.dirname(filename))
    return filename


def get_open_filename(titletext="Open", config=None):
    Tk().withdraw()
    initial_dir = get_initial_dir(config)
    filename = tkinter.filedialog.askopenfilename(title=titletext, initialdir=initial_dir)
    set_initial_dir(config, os.path.dirname(filename))
    return filename


def set_initial_dir(config, initial_dir):
    if config and initial_dir is not None:
        if not config.has_section('Section1'):
            config.add_section('Section1')
        config.set('Section1', 'initial_dir', initial_dir)


def get_initial_dir(config):
    if config and config.has_section('Section1'):
        return config.get('Section1', 'initial_dir')
    else:
        return os.getcwd()


def save_data(filename_save, data):
    f = open(filename_save, mode='w')
    f.writelines(data)
    f.close()


config = ConfigParser.RawConfigParser()
sampling_freq = 1250
features_id = [5, 8]
channel = range(3, 7)
window_size = 0.3  # seconds
window_size_sample_unit = int(window_size * sampling_freq)
overlapping_size = 0.05  # seconds
overlapping_size_sample_unit = int(overlapping_size * sampling_freq)

# filename = 'F:\\Derek_Desktop_Backup\\Marshal\\20190705_Chronic_NHP_wireless_implant_Alvin\\improvedClassifier\\biceps_multi_1_20190705.csv'
# filename = 'F:\\Derek_Desktop_Backup\\Marshal\\20190705_Chronic_NHP_wireless_implant_Alvin\\improvedClassifier\\tricpes_multi_merged_20190705.csv'
# filename = 'F:\\Derek_Desktop_Backup\\Marshal\\20190705_Chronic_NHP_wireless_implant_Alvin\\improvedClassifier\\baseline_20190626.csv'
# filename = 'F:\\Derek_Desktop_Backup\\Marshal\\20190705_Chronic_NHP_wireless_implant_Alvin\\20190705_data_all.csv'
filename = get_open_filename("Open data file", config)
print("data filename: " + filename)

# filename_clf = 'F:\\Derek_Desktop_Backup\\Marshal\\20190705_Chronic_NHP_wireless_implant_Alvin\\improvedClassifier\\Info\\classificationTmp\\classifierCha3.sav'
# filename_norms = 'F:\\Derek_Desktop_Backup\\Marshal\\20190705_Chronic_NHP_wireless_implant_Alvin\\improvedClassifier\\Info\\classificationTmp\\normsCha3.csv'

# filename_clf = 'F:\\Derek_Desktop_Backup\\Marshal\\20190626_Chronic_NHP_wireless_implant_Alvin\\baselineBurstDetection\\Info\\classificationTmp\\300ms windowsize\\classifierCha.sav'
# filename_norms = 'F:\\Derek_Desktop_Backup\\Marshal\\20190626_Chronic_NHP_wireless_implant_Alvin\\baselineBurstDetection\\Info\\classificationTmp\\300ms windowsize\\normsCha.csv'

# filename_clf = 'F:\\Derek_Desktop_Backup\\Marshal\\20190626_Chronic_NHP_wireless_implant_Alvin\\baselineBurstDetection\\Info\\classificationTmp\\classifierCha3.sav'
# filename_norms = 'F:\\Derek_Desktop_Backup\\Marshal\\20190626_Chronic_NHP_wireless_implant_Alvin\\baselineBurstDetection\\Info\\classificationTmp\\normsCha3.csv'

filename_clf = get_open_filename("Open classifier file", config)
print("classifier filename: " + filename_clf)
filename_norms = get_open_filename("Open norms file", config)
print("norms filename: " + filename_norms)

print("reading data file...")
data_all = np.genfromtxt(filename, delimiter=',', skip_header=True)
data_channel = data_all[:, channel]
print("reading classifier file...")
clf = pickle.load(open(filename_clf, 'rb'))  # there should only be one classifier file
print("reading norms file...")
norms = np.genfromtxt(filename_norms, delimiter=',')

print("extracting features...")
features = get_window_features(data_channel, window_size_sample_unit, overlapping_size_sample_unit)
features = features / norms

print("generating prediction...")
length_data = np.size(data_channel, 0)
prediction = get_prediction_all(clf, features, overlapping_size_sample_unit, length_data) - 1
prediction[prediction < 0] = 0

print("getting saving filename...")
filename_prediction = get_save_filename("Save prediction as", config, 'prediction') + ".csv"

print("saving prediction: " + filename_prediction)
save_data(filename_prediction, [str(x)+'\n' for x in prediction])

plt.plot(prediction)
plt.show()

print("done...")



