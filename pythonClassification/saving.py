import os
import datetime
import numpy as np


class Saving:  # save the data
    def __init__(self):
        now = datetime.datetime.now()
        self.__saving_dir_Date = "%d%02d%02d" % (now.year, now.month, now.day)
        self.__saving_filename = "data%s%02d%02d%02d%02d" % (
            self.__saving_dir_Date, now.hour, now.minute, now.second, now.microsecond)
        self.__saving_full_filename = os.path.join("Data", self.__saving_dir_Date, self.__saving_filename) + ".csv"

        self.__create_saving_dir()  # create saving directory, skip if the file exists

    def __create_saving_dir(self):
        if not os.path.exists(os.path.join("Data", self.__saving_dir_Date)):
            os.makedirs(os.path.join("Data", self.__saving_dir_Date))

    def save(self, data, *args):  # save the data
        saving_file_obj = open(self.__saving_full_filename, *args)
        np.savetxt(saving_file_obj, data, fmt="%f", delimiter=",")
        saving_file_obj.close()
