import _winreg as winreg
import itertools
from serial import SerialException, Serial

READ_COMMAND = 'r'
WRITE_COMMAND = 'w'
ID_COMMAND = 'i'

SUCCESS_RESPONSE = 's'
COMMAND_FAILURE_RESPONSE = 'c'
SEND_DELAY_RESPONSE = 'd'
RANGE_FAILURE_RESPONSE = 'r'
HANDSHAKE_RESPONSE = 'h'

TERM_SEQ_READ = '\r\n'
TERM_SEQ_WRITE = '\n'

BAUDRATE = 115200
TIMEOUT = 5

class SerialLineTransceiverException(Exception): pass

class SerialLineTransceiver:
    def __init__(self,ser):
        self.ser = ser
    def write_line(self,s):
        self.ser.write(s + TERM_SEQ_WRITE)
    def read_line(self):
        s = ''
        while True:
            c = self.ser.read()
            if c == '':
                raise SerialLineTransceiverException('timeout before line read')
            s += c
            if s[-1 * len(TERM_SEQ_READ):] == TERM_SEQ_READ:
                return s[:-1 * len(TERM_SEQ_READ)]

class DelayGeneratorException(Exception): pass

class DelayGenerator(SerialLineTransceiver):
    BAUDRATE=115200
    TIMEOUT=5
    def __init__(self,id):
        SerialLineTransceiver.__init__(self,self.init_delay_generator(id))

    def get_delay(self):
        self.write_line(READ_COMMAND)
        delay = int(self.read_line())
        self.read_line()
        return delay

    def set_delay(self,delay):
        self.write_line(WRITE_COMMAND)
        self.read_line() # ddg responds with SEND_DELAY_RESPONSE
        self.write_line(str(delay))
        response = self.read_line() # ddg responds with SUCCESS_RESPONSE or RANGE_FAILURE_RESPONSE
        if response == RANGE_FAILURE_RESPONSE:
            raise DelayGeneratorException('requested delay out of range')

    @classmethod
    def init_delay_generator(cls,id):
        for port,_ in cls.enumerate_serial_ports():
            try:
                ser = Serial(
                    port=port,
                    baudrate=BAUDRATE,
                    timeout=TIMEOUT
                )
            except SerialException:
                continue
            try:
                line_trans = SerialLineTransceiver(ser)
                if cls._handshakes(line_trans) and id == cls._get_id(line_trans):
                    return ser
            except SerialLineTransceiverException:
                continue
        raise DelayGeneratorException('device id %d not found' % id)

    @staticmethod
    def _handshakes(line_trans):
        handshake = line_trans.read_line()
        return handshake == HANDSHAKE_RESPONSE

    @staticmethod
    def _get_id(line_trans):
        line_trans.write_line(ID_COMMAND)
        id = int(line_trans.read_line())
        line_trans.read_line()
        return id

    @staticmethod
    def enumerate_serial_ports():
        """ Uses the Win32 registry to return a iterator of serial 
            (COM) ports existing on this computer.
        """
        path = 'HARDWARE\\DEVICEMAP\\SERIALCOMM'
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
        except WindowsError:
            raise IterationError

        for i in itertools.count():
            try:
                val = winreg.EnumValue(key, i)
                yield (str(val[1]), str(val[0]))
            except EnvironmentError:
                break


if __name__ == '__main__':
    for i in range(5):
        dg = DelayGenerator(i)
        print i, dg.get_delay()
