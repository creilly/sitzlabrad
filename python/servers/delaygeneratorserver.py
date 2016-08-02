from deviceserver import device_setting, Device, DeviceSignal, DeviceServer
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

class DelayGeneratorDevice(Device):
    on_new_delay = DeviceSignal(110,ON_NEW_DELAY,'i')

    def __init__(self,dg):
        Device.__init__(self)
        self.dg = dg

    @device_setting(10, returns='i')
    def get_delay(self,c):
        return self.dg.get_delay()

    @device_setting(13, device_setting_lockable=True, delay='i')
    def set_delay(self,c,delay):
        self.dg.set_delay(delay)
        self.on_new_delay(delay)

class DelayGeneratorServer(DeviceServer):
    name = NAME
    device_class = DelayGeneratorDevice

    @inlineCallbacks
    def initServer(self):  # Do initialization here
        self.delay_generators = {}
        reg = self.client.registry
        yield reg.cd(REGISTRY_PATH)
        _, dg_names = yield reg.dir()        
        for name in dg_names:
            dg_id = yield reg.get(name)
            self.add_device(
                name,
                DelayGeneratorDevice(
                    DelayGenerator(dg_id)
                )
            )
        yield DeviceServer.initServer(self)

__server__ = DelayGeneratorServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
