from serialtransceiver import HandshakeSerialDevice
import socket

READ_COMMAND = 'r'
WRITE_COMMAND = 'w'
ID_COMMAND = 'i'

SUCCESS_RESPONSE = 's'
COMMAND_FAILURE_RESPONSE = 'c'
SEND_DELAY_RESPONSE = 'd'
RANGE_FAILURE_RESPONSE = 'r'
HANDSHAKE_RESPONSE = 'h'

BAUDRATE=115200

TIMEOUT=2

class DelayGeneratorException(Exception): pass

class DelayGenerator(HandshakeSerialDevice):

    def __init__(self,id):
        HandshakeSerialDevice.__init__(
            self,
            HANDSHAKE_RESPONSE,
            ID_COMMAND,
            id,
            BAUDRATE,
            TIMEOUT
        )

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

class DAQmxDelayGenerator:
    SET_DELAY = 's'
    GET_DELAY = 'g'
    def __init__(self,addr,port):
        self.addr = addr
        self.port = port

    def get_connection(self):
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.connect((self.addr, self.port))
        return conn

    def get_delay(self):
        conn = self.get_connection()
        conn.send(self.GET_DELAY + '\n')
        response = conn.recv(512)
        return int(response)

    def set_delay(self,delay):
        conn = self.get_connection()
        conn.send(self.SET_DELAY + ' ' + str(delay) + '\n')
        response = conn.recv(512)

if __name__ == '__main__':
    print '---------- daqmx dg ----------\n'
    addr = raw_input('enter ip addr of daqmx host (press enter for localhost): ')
    addr = addr if addr else 'localhost'
    port = int(raw_input('enter port of daqmx host: '))
    daqmx_dg = DAQmxDelayGenerator(addr,port)
    print 'initial delay', daqmx_dg.get_delay()
    daqmx_dg.set_delay(int(raw_input('enter delay: ')))
    raw_input('press enter to get query delay')
    print 'new delay', daqmx_dg.get_delay()
    print '\n--------- arduino dg ---------\n'
    for i in range(5):
        dg = DelayGenerator(i)
        print i, dg.get_delay()


