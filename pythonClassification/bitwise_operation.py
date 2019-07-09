def set_bit(value, index):
    return value | 1 << index


def clear_bit(value, index):
    return value & ~(1 << index)


def edit_bit(index, state, value):
    if state:
        return set_bit(value, index)
    else:
        return clear_bit(value, index)


def check_bit(value, index):
    return value >> index & 1
