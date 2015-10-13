from twisted.internet.defer import inlineCallbacks, returnValue

class VoltmeterClient:
    def __init__(self,vm_server,channel):
        self.vm_server = server
        self.channel = channel

    def get_sample(self):
        return self.vm_server.get_sample(self.channel)

    @inlineCallbacks
    def get_average(self,count):
        average = 0.
        for _ in range(count):
            sample = yield self.get_sample()
            average += sample
        average = average / count
        returnValue(average)

        
