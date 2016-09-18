from serialtransceiver import HandshakeSerialDevice

READ_COMMAND = 'r'
WRITE_COMMAND = 'w'
ID_COMMAND = 'i'

SUCCESS_RESPONSE = 's'
COMMAND_FAILURE_RESPONSE = 'c'
SEND_DELAY_RESPONSE = 'd'
RANGE_FAILURE_RESPONSE = 'r'
HANDSHAKE_RESPONSE = 'h'

BAUDRATE=115200
TIMEOUT=5

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

if __name__ == '__main__':
    for i in range(5):
        dg = DelayGenerator(i)
        print i, dg.get_delay()
