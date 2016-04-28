class DAQmxException(Exception):
    def __init__(self,code,message):
        self.code = code
        self.message = message
        Exception.__init__(
            self,
            'daqmx error code %d: %s' % (code,message)
        )

