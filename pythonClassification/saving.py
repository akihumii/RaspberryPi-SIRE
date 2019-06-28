import os
import datetime
import numpy as np


class Saving:  # save the data
    def __init__(self, saving_filename=''):
        if saving_filename:
            self.__saving_full_filename = saving_filename
        else:
            self.__saving_full_filename = os.path.join("Data", self.get_filename()) + ".csv"

        self.__create_saving_dir()  # create saving directory, skip if the file exists

    def __create_saving_dir(self):
        if not os.path.exists("Data"):
            os.makedirs("Data")

    def get_filename(self):
        now = datetime.datetime.now()
        saving_dir_date = "%d%02d%02d" % (now.year, now.month, now.day)
        saving_filename = "data%s%02d%02d%02d%02d" % (
            saving_dir_date, now.hour, now.minute, now.second, now.microsecond)

        return saving_filename

    def save(self, data, *args):  # save the data
        saving_file_obj = open(self.__saving_full_filename, *args)
        np.savetxt(saving_file_obj, data, fmt="%f", delimiter=",")
        saving_file_obj.close()
