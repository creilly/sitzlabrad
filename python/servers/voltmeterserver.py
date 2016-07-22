from lockserver import LockServer, lockable_setting
from labrad.server import setting, Signal
from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.python.failure import Failure
import labrad
from daqmx.task.ai import AITask
from twisted.internet.threads import deferToThread
import numpy as np
from functools import partial
from time import sleep

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

AVAILABLE_CHANNELS = 'available channels'
DEFAULT_CHANNELS = 'default channels'
TRIGGERING = 'triggering'
TRIGGER_SOURCE = 'trigger source'
TRIGGER_EDGE = 'trigger edge'
SAMPLING_DURATION = 'sampling duration'

ON_ACTIVE_CHANNELS_CHANGED = 'on_active_channels_changed'
ON_SAMPLING_DURATION_CHANGED = 'on_sampling_duration_changed'
ON_TRIGGERING_CHANGED = 'on_triggering_changed'

class VoltmeterServer(LockServer):
    name = NAME

    on_active_channels_changed = Signal(110,ON_ACTIVE_CHANNELS_CHANGED,'*s')
    on_sampling_duration_changed = Signal(111,ON_SAMPLING_DURATION_CHANGED,'v')
    on_triggering_changed = Signal(112,ON_TRIGGERING_CHANGED,'b')

    @inlineCallbacks
    def initServer(self):  # Do initialization here
        reg = self.client.registry
        yield reg.cd(REGISTRY_PATH)
        self.available_channels = yield reg.get(AVAILABLE_CHANNELS)
        default_channels = yield reg.get(DEFAULT_CHANNELS)
        triggering = yield reg.get(TRIGGERING)
        self.trigger_source = yield reg.get(TRIGGER_SOURCE)
        self.trigger_edge = yield reg.get(TRIGGER_EDGE)
        sampling_duration = yield reg.get(SAMPLING_DURATION)
        self._set_active_channels(
            default_channels,
            triggering=triggering,
            sampling_duration=sampling_duration
        )
        self.acquiring = False
        self.subscribers = []
        self.queue = []
        yield LockServer.initServer(self)
    
    @inlineCallbacks
    def start_acquisition(self):
        self.acquiring = True
        samples = yield deferToThread(self.task.acquire_samples)
        self.acquiring = False
        averages = {
            channel:np.average(series) 
            for channel, series in samples.items()
        }
        while self.queue:
            self.queue.pop(0)()
        for d, channel in self.subscribers:
            try:
                d.callback(averages[channel])
            except KeyError, e:
                d.errback(e)
        self.subscribers = []

    @setting(10, channel='s', returns='v')    
    def get_sample(self,c,channel):
        if not self.subscribers:
            self.start_acquisition()
        d = Deferred()
        self.subscribers.append((d,channel))
        return d        

    @setting(11, returns='*s')
    def get_available_channels(self,c):
        return self.available_channels

    @setting(12, returns='*s')
    def get_active_channels(self,c):
        return self.task.get_channels()

    @lockable_setting(13,channels='*s')
    def set_active_channels(self,c,channels):
        if not channels:
            raise Exception('must have at least one active channel')
        if self.acquiring:
            self.queue.append(partial(self._set_active_channels,channels))
        else:
            self._set_active_channels(channels)
    @setting(14, channel='s', returns='s')
    def get_units(self,c,channel):
        return AITask(channel).get_units()[channel]

    @lockable_setting(15, duration = 'v')
    def set_sampling_duration(self,c,duration):
        if self.acquiring:
            self.queue.append(
                partial(
                    self._set_sampling_duration,
                    duration
                )
            )
        else:
            self._set_sampling_duration(duration)

    @setting(16, returns='v')
    def get_sampling_duration(self,c):
        return self._get_sampling_duration()

    @setting(17, returns='b')
    def is_triggering(self,c):
        return self.task.is_triggering()

    @lockable_setting(18, is_triggering='b')
    def set_triggering(self,c,is_triggering):
        if self.acquiring:
            self.queue.append(
                partial(
                    self._set_triggering,is_triggering
                )
            )
        else:
            self._set_triggering(is_triggering)

    def _set_active_channels(self,channels,triggering=None,sampling_duration=None):
        task = AITask(*list(channels)) # list cast necessary to handle LazyList output from registry call
        if sampling_duration is None:
            sampling_duration = self._get_sampling_duration()
        if triggering is None:
            triggering = self.task.is_triggering()        
        task.set_sampling_rate(task.get_max_sampling_rate())
        self.task = task
        self._set_triggering(triggering)
        self._set_sampling_duration(sampling_duration)
        self.on_active_channels_changed(channels)

    def _set_sampling_duration(self,duration):
        sample_quantity = int(
            duration*self.task.get_sampling_rate()
        )
        self.task.set_sample_quantity(sample_quantity)
        self.on_sampling_duration_changed(
            self._get_sampling_duration()
        )

    def _get_sampling_duration(self):
        return self.task.get_sample_quantity()/self.task.get_sampling_rate()

    def _set_triggering(self,is_triggering):
        if is_triggering:
            self.task.set_trigger(
                self.trigger_source,
                self.trigger_edge
            )
        else:
            self.task.unset_trigger()
        self.on_triggering_changed(is_triggering)

__server__ = VoltmeterServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
