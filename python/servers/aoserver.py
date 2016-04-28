from labrad.server import LabradServer, setting, Signal
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

ON_NEW_VALUE = 'on_new_value'

DEFAULT_VALUE = 0.

class AnalogOutputServer(LabradServer):
    name = NAME

    on_new_value = Signal(110,ON_NEW_VALUE,'(sv)')

    @inlineCallbacks
    def initServer(self):
        reg = self.client.registry
        reg.cd(REGISTRY_PATH)
        channels = self.channels = yield reg.get(CHANNELS)
        self.tasks = {
            channel:AOTask(channel)
            for channel in channels
        }
        self.values = {}
        for channel in channels:
            self._set_value(channel,DEFAULT_VALUE)
        yield LabradServer.initServer(self)

    @setting(10, channel='s', value='v')  
    def set_value(self,c,channel,value):
        self._set_value(channel,value)
        self.on_new_value((channel,value))
        
    @setting(11, channel='s', returns='v')
    def get_value(self,c,channel):
        return self.values[channel]
        
    @setting(12, returns='*s')
    def get_channels(self,c):
        return self.channels

    @setting(13, channel='s', returns='s')
    def get_units(self,c,channel):
        return self.tasks[channel].get_units()

    @setting(14, channel='s', returns='(vv)')
    def get_range(self,c,channel):
        task = self.tasks[channel]
        return (
            task.get_min(),
            task.get_max()
        )

    def _set_value(self,channel,value):
        self.tasks[channel].write_sample(value)
        self.values[channel] = value

__server__ = AnalogOutputServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
