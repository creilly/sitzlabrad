from deviceserver import device_setting, Device, DeviceSignal, DeviceServer
from labrad.server import LabradServer, setting, Signal
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue
from delaygenerator import DelayGenerator, DAQmxDelayGenerator
from twisted.internet.threads import deferToThread

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
REGISTRY_PATH = ['','Servers',NAME,'dgs']

ON_NEW_DELAY = 'on_new_delay'

CLASS = 'class'
ARDUINO = 'arduino'
DAQMX = 'daqmx'
ID = 'id'
ADDR = 'addr'
PORT = 'port'

class DelayGeneratorDevice(Device):
    on_new_delay = DeviceSignal(110,ON_NEW_DELAY,'i')

    def __init__(self,dg):
        Device.__init__(self)
        self.dg = dg

    @device_setting(10, returns='i')
    def get_delay(self,c):
        delay = yield deferToThread(self.dg.get_delay)
        returnValue(delay)

    @device_setting(13, device_setting_lockable=True, delay='i')
    def set_delay(self,c,delay):
        yield deferToThread(self.dg.set_delay,delay)
        self.on_new_delay(delay)

class DelayGeneratorServer(DeviceServer):
    name = NAME
    device_class = DelayGeneratorDevice

    @inlineCallbacks
    def initServer(self):
        self.delay_generators = {}
        reg = self.client.registry
        yield reg.cd(REGISTRY_PATH)
        dg_names, _ = yield reg.dir()        
        for name in dg_names:
            reg.cd(name)
            _, keys = yield reg.dir()
            if CLASS in keys:
                dg_class = yield reg.get(CLASS)
            else:
                dg_class = 'arduino'
            if dg_class == ARDUINO:
                dg_id = yield reg.get(ID)
                self.add_device(
                    name,
                    DelayGeneratorDevice(
                        DelayGenerator(dg_id)
                    )
                )
            if dg_class == DAQMX:
                if ADDR in keys:
                    addr = yield reg.get(ADDR)
                else:
                    addr = 'localhost'
                port = yield reg.get(PORT)
                self.add_device(
                    name,
                    DelayGeneratorDevice(
                        DAQmxDelayGenerator(addr,port)
                    )
                )
            reg.cd('..')
        yield DeviceServer.initServer(self)

__server__ = DelayGeneratorServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
