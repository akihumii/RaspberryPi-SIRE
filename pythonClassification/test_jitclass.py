from bag import Bag
from filtering import Filtering


if __name__ == "__main__":
    a = Bag(3)
    print(a.increment(3))

    b = Filtering(1250,200,500,50)
    print('Finished...')