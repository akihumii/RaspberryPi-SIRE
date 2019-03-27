import os
import datetime
import numpy as np


class Saving:  # save the data
    def __init__(self, method='Data'):
        now = datetime.datetime.now()
        self._saving_dir_Date = "%d%02d%02d" % (now.year, now.month, now.day)
        self._saving_filename = "data%s%02d%02d%02d%02d" % (
            self._saving_dir_Date, now.hour, now.minute, now.second, now.microsecond)
        
        self._create_saving_dir()  # create saving directory, skip if the file exists
        
        self.methods = {
            'Data': self._create_saving_dir(),
            'Training': self._create_training_dir()
        }
        self._saving_full_filename = self.methods.get(method)

    def _create_training_dir(self):  # just add on the number without having postfix of timestamps
        if not os.path.exists(os.path.join("Data", "Training")):
            os.makedirs(os.path.join("Data", "Training"))

        file_name = [f for f in os.listdir(os.path.join("Data", "Training")) if f.startswith('training')]
        training_id = 0
        if file_name:
            training_id = file_name[-1][8]

        return os.path.join("Data", "Training", "training%d") % training_id + ".csv"
    
    def _create_saving_dir(self):
        if not os.path.exists(os.path.join("Data", self._saving_dir_Date)):
            os.makedirs(os.path.join("Data", self._saving_dir_Date))

        return os.path.join("Data", self._saving_dir_Date, self._saving_filename) + ".csv"

    def save(self, data, *args):  # save the data
        saving_file_obj = open(self._saving_full_filename, *args)
        np.savetxt(saving_file_obj, data, fmt="%f", delimiter=",")
        saving_file_obj.close()
