import _winreg as winreg
import itertools
from serial import SerialException, Serial

TERM_SEQ_READ = '\r\n'
TERM_SEQ_WRITE = '\n'

class SerialLineTransceiverException(Exception): pass

class SerialLineTransceiver:
    def __init__(
        self,
        ser,
        term_seq_read=TERM_SEQ_READ,
        term_seq_write=TERM_SEQ_WRITE,
    ):
        self.ser = ser
        self.term_seq_read=term_seq_read
        self.term_seq_write=term_seq_write
    def write_line(self,s):
        self.ser.write(s + self.term_seq_write)
    def read_line(self):
        tsr = self.term_seq_read
        s = ''
        while True:
            c = self.ser.read()
            if c == '':
                raise SerialLineTransceiverException('timeout before line read')
            s += c
            if s[-1 * len(tsr):] == tsr:
                return s[:-1 * len(tsr)]

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

class HandshakeSerialDeviceException(Exception): pass

BAUDRATE = 115200
TIMEOUT = 5

class HandshakeSerialDevice(SerialLineTransceiver):
    def __init__(self,handshake_char,id_char,id,baudrate=BAUDRATE,timeout=TIMEOUT):
        SerialLineTransceiver.__init__(
            self,
            self._init(
                handshake_char,
                id_char,
                id,
                baudrate,
                timeout
            )
        )

    @classmethod
    def _init(cls,handshake_char,id_char,id,baudrate,timeout):
        for port,_ in cls.enumerate_serial_ports():
            try:
                ser = Serial(
                    port=port,
                    baudrate=baudrate,
                    timeout=timeout
                )
            except SerialException, s:
                continue
            try:
                line_trans = SerialLineTransceiver(ser)
                if cls._handshakes(line_trans,handshake_char) and id == cls._get_id(line_trans,id_char):
                    return ser
            except SerialLineTransceiverException:
                continue
        raise HandshakeSerialDeviceException('device id %d not found' % id)

    @staticmethod
    def _handshakes(line_trans,handshake_char):
        handshake = line_trans.read_line()
        return handshake == handshake_char

    @staticmethod
    def _get_id(line_trans,id_char):
        line_trans.write_line(id_char)
        return int(line_trans.read_line())

