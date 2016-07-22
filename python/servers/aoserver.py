from deviceserver import DeviceServer, device_setting, DeviceSignal, Device
from twisted.internet.defer import inlineCallbacks, Deferred
import labrad
from daqmx.task import Task
from daqmx.task.ao import AOTask
from twisted.internet.threads import deferToThread
import numpy as np

"""
### BEGIN NODE INFO
[info]
name = Analog Output
version = 1.0
description = output analog voltages from daqmx device
[startup]
cmdline = %PYTHON% %FILE%
timeout = 20
[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

NAME = 'Analog Output'
REGISTRY_PATH = ['','Servers',NAME]
CHANNELS = 'channels'

ON_NEW_VALUE = 'on new value'

DEFAULT_VALUE = 0.

class AnalogOutputDevice(Device):
    on_new_value = DeviceSignal(110,ON_NEW_VALUE,'v')
    def __init__(self,task,default_value=0.):
        Device.__init__(self)
        self.task = task
        self._set_value(default_value)

    @device_setting(10, device_setting_lockable=True, value='v')  
    def set_value(self,c,value):
        self._set_value(value)
        
    @device_setting(11, returns='v')
    def get_value(self,c):
        return self.values
        
    @device_setting(13, returns='s')
    def get_units(self,c):
        return self.task.get_units()

    @device_setting(14, returns='(vv)')
    def get_range(self,c):
        return (
            self.task.get_min(),
            self.task.get_max()
        )

    def _set_value(self,value):
        self.task.write_sample(value)
        self.values = value
        self.on_new_value(value)

class AnalogOutputServer(DeviceServer):
    name = NAME
    device_class = AnalogOutputDevice

    @inlineCallbacks
    def initServer(self):
        reg = self.client.registry
        reg.cd(REGISTRY_PATH)
        channels = self.channels = yield reg.get(CHANNELS)
        for channel in channels:
            self.add_device(
                channel,AnalogOutputDevice(AOTask(channel))
            )
        yield DeviceServer.initServer(self)

__server__ = AnalogOutputServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
