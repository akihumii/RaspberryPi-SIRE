def set_bit(value, index):
    return value | 1 << index


def clear_bit(value, index):
    return value & ~(1 << index)
