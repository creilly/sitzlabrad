from twisted.internet.defer import inlineCallbacks, returnValue
ON_ACTIVE_CHANNELS_CHANGED = 210
ON_SAMPLING_DURATION_CHANGED = 211
class VoltmeterClient:
    def __init__(self,vm_server):
        self.vm_server = vm_server
        self.on_active_channels_changed_cb = None
        vm_server.on_active_channels_changed(
            ON_ACTIVE_CHANNELS_CHANGED
        )
        vm_server.addListener(
            listener=self._on_active_channels_changed,
            source=None,
            ID=ON_ACTIVE_CHANNELS_CHANGED
        )
        self.on_sampling_duration_changed_cb = None
        vm_server.on_sampling_duration_changed(
            ON_SAMPLING_DURATION_CHANGED
        )
        vm_server.addListener(
            listener=self._on_sampling_duration_changed,
            source=None,
            ID=ON_SAMPLING_DURATION_CHANGED
        )
    def _on_active_channels_changed(self,c,msg):
        cb = self.on_active_channels_changed_cb
        if cb is not None: cb(msg)

    def on_active_channels_changed(self,cb):
        self.on_active_channels_changed_cb = cb

    def _on_sampling_duration_changed(self,c,msg):
        cb = self.on_sampling_duration_changed_cb
        if cb is not None: cb(msg)

    def on_sampling_duration_changed(self,cb):
        self.on_sampling_duration_changed_cb = cb

class ChannelClient:
    def __init__(self,vm_server,channel):
        self.vm_server = vm_server
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

        
