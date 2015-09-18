READ_COMMAND = 'r'
WRITE_COMMAND = 'w'
ID_COMMAND = 'i'

SUCCESS_RESPONSE = 's'
COMMAND_FAILURE_RESPONSE = 'c'
SEND_DELAY_RESPONSE = 'd'
RANGE_FAILURE_RESPONSE = 'r'

TERM_CHAR = '\n'

class DelayGeneratorRangeFailure(Exception): pass

class DelayGenerator:
    def __init__(self,ser):
        self.ser = ser
    def get_id(self):
        self.write_line(ID_COMMAND)
        id = int(self.read_line()) # ddg responds with device id
        self.read_line() # ddg responds with SUCCESS_RESPONSE
        return id
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
        if response is RANGE_FAILURE_RESPONSE:
            raise DelayGeneratorRangeFailure()
    def write_line(self,s):
        self.ser.write(s + TERM_CHAR)
    def read_line(self):
        s = ''
        while True:
            c = self.ser.read()
            if c is TERM_CHAR:
                return s
            s += c
                
        
        
