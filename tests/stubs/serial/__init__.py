# Stub de pyserial: CONNECTED controla si "hay un Arduino enchufado".
class SerialException(Exception):
    pass


CONNECTED = False
WRITTEN = []  # bytes que se mandaron al "Arduino"


def reset_state():
    global CONNECTED, WRITTEN
    CONNECTED = False
    WRITTEN = []


class Serial:
    def __init__(self, port, baud, timeout=1):
        if not CONNECTED:
            raise SerialException(f"could not open port {port}: [Errno 2] del dispositivo")
        self.port = port
        self.baud = baud
        self._open = True

    @property
    def is_open(self):
        return self._open

    def write(self, b):
        if not self._open:
            raise SerialException("Port is closed")
        WRITTEN.append(b)

    def flush(self):
        pass

    def readline(self):
        import time

        time.sleep(0.005)
        return b""

    def close(self):
        self._open = False