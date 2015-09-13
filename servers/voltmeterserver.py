from labrad.server import LabradServer, setting
from twisted.internet.defer import inlineCallbacks, Deferred
import labrad
from daqmx.task.ai import AITask
from twisted.internet.threads import deferToThread
import numpy as np

"""
### BEGIN NODE INFO
[info]
name = Voltmeter
version = 1.0
description = monitor dc voltages on daqmx device
[startup]
cmdline = %PYTHON% %FILE%
timeout = 20
[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

NAME = 'Voltmeter'
REGISTRY_PATH = ['','Servers',NAME]
TASK_NAME = 'task'

class VoltmeterServer(LabradServer):
    name = NAME

    @inlineCallbacks
    def initServer(self):  # Do initialization here
        reg = self.client.registry
        yield reg.cd(REGISTRY_PATH)
        task_name = yield reg.get(TASK_NAME)
        self.ai_task = AITask(task_name)
        self.subscribers = []
        yield LabradServer.initServer(self)

    @inlineCallbacks
    def start_acquisition(self):
        samples = yield deferToThread(self.ai_task.acquire_samples)
        averages = {
            channel:np.average(series) for channel, series in samples.items()
            }
        for d, channel in self.subscribers:
            d.callback(averages[channel])
        self.subscribers = []

    @setting(10, channel='s', returns='v')
    def get_sample(self,c,channel):
        if not self.subscribers:
            self.start_acquisition()
        d = Deferred()
        self.subscribers.append((d,channel))
        return d

    @setting(11, returns='*s')
    def get_channels(self,c):
        return self.ai_task.get_channels()

__server__ = VoltmeterServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
