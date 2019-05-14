from numba.decorators import jit

@jit
def plus_one(my_field):
    return my_field+1


class my_class:
    def __init__(self):
        self.my_field = 3


if __name__ == "__main__":
    a = my_class()
    r = plus_one(a.my_field)
    print(r)
