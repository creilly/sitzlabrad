from labrad.server import LabradServer, setting, Signal
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue
from delaygenerator import DelayGenerator

"""
### BEGIN NODE INFO
[info]
name = Delay Generator
version = 1.0
description = manages all connected delay generators
[startup]
cmdline = %PYTHON% %FILE%
timeout = 20
[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

NAME = 'Delay Generator'
REGISTRY_PATH = ['','Servers',NAME]

ON_NEW_DELAY = 'on_new_delay'

class DelayGeneratorServer(LabradServer):
    name = NAME
    on_new_delay = Signal(110,ON_NEW_DELAY,'(ii)')

    @inlineCallbacks
    def initServer(self):  # Do initialization here
        self.delay_generators = {}
        reg = self.client.registry
        yield reg.cd(REGISTRY_PATH)
        _, dg_names = yield reg.dir()        
        for name in dg_names:
            dg_id = yield reg.get(name)
            self.delay_generators[dg_id] = DelayGenerator(dg_id)
        yield LabradServer.initServer(self)

    @setting(10, id='i', returns='i')
    def get_delay(self,c,id):
        return self.delay_generators[id].get_delay()

    @setting(13, id='i', delay='i')
    def set_delay(self,c,id,delay):
        self.delay_generators[id].set_delay(delay)
        self.on_new_delay((id,delay))

    @setting(11, returns='*i')
    def get_delay_generators(self,c):
        return self.delay_generators.keys()

    @setting(12, id='i', returns='s')
    def get_name(self,c,id):
        reg = self.client.registry 
        yield reg.cd(REGISTRY_PATH)
        _, dg_names = yield reg.dir()
        for name in dg_names:
            dg_id = yield reg.get(name)
            if dg_id == id:
                returnValue(name)

__server__ = DelayGeneratorServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
