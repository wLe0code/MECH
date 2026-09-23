COMPORTS = []  # lista de objetos con .device/.description/.manufacturer


def reset_state():
    global COMPORTS
    COMPORTS = []


def comports():
    return list(COMPORTS)