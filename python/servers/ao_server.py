from labrad.server import LabradServer, setting
from twisted.internet.defer import inlineCallbacks, Deferred
import labrad
from daqmx.task import Task
from daqmx.task.ao import AOTask
from twisted.internet.threads import deferToThread
import numpy as np

"""
### BEGIN NODE INFO
[info]
name = Analog Output Server
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
TASK_NAME = 'analog output task'

ON_VALUE_CHANGED = 'on_value_changed'

class VoltmeterServer(LabradServer):
    name = NAME    

    on_value_changed = Signal(110,ON_VALUE_CHANGED,'(sv)')

    @inlineCallbacks
    def initServer(self):  # Do initialization here
        self.ao_tasks = {
            task_name:AOTask(task_name,channel) for channel in Task.get_global_channels()[Task.AO]
        }
        yield LabradServer.initServer(self)

    @setting(10, channel='s', value, returns='v')    
    def write_sample(self,c,channel,sample):
        self.ao_tasks[channel].write_sample(sample)
        

    @setting(11, returns='*s')
    def get_channels(self,c):
        return self.ao_tasks.keys()

    @setting(12, returns='s')
    def get_units(self,c,channel):
        return self.ao_tasks[channel].get_units()

__server__ = VoltmeterServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
