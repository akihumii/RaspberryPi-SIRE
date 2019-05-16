import numpy as np
from bag import Bag
from filtering import Filtering
from custom_filter import CustomFilter


if __name__ == "__main__":
    # a = Bag(3)
    # print(a.increment(3))

    data = np.arange(100)
    b = CustomFilter(200,500,50,10,1250)
    print('created custom filter class...')
    b.set_filter()
    print('finished setting filter...')
    for i in range(1000):
        result = b.filter_data(data)
        print(i)

    # b = Filtering(1250,200,500,50)
    print('Finished...')