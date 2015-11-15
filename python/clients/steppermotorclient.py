ON_NEW_POSITION = 210
ON_BUSY_STATUS_CHANGED = 211
ON_ENABLED_STATUS_CHANGED = 212
class StepperMotorClient:
    def __init__(self,sm_name,sm_server):
        self.sm_name = sm_name
        self.sm_server = sm_server
        self.on_new_position_cb = None
        self.on_busy_status_changed_cb = None
        self.on_enabled_status_changed_cb = None
        sm_server.on_new_position(ON_NEW_POSITION)
        sm_server.addListener(
            listener=self._on_new_position,source=None,ID=ON_NEW_POSITION
        )
        sm_server.on_busy_status_changed(ON_BUSY_STATUS_CHANGED)
        sm_server.addListener(
            listener=self._on_busy_status_changed,source=None,ID=ON_BUSY_STATUS_CHANGED
        )
        sm_server.on_enabled_status_changed(ON_ENABLED_STATUS_CHANGED)
        sm_server.addListener(
            listener=self._on_enabled_status_changed,source=None,ID=ON_ENABLED_STATUS_CHANGED
        )

    def _on_new_position(self,c,msg):
        cb = self.on_new_position_cb
        if cb is not None and msg[0] == self.sm_name:
            cb(msg[1])
            
    def on_new_position(self,cb):
        self.on_new_position_cb = cb

    def _on_busy_status_changed(self,c,msg):
        cb = self.on_busy_status_changed_cb
        if cb is not None and msg[0] == self.sm_name:
            cb(msg[1])

    def on_busy_status_changed(self,cb):
        self.on_busy_status_changed_cb = cb

    def is_busy(self):
        return self.sm_server.is_busy(self.sm_name)

    def _on_enabled_status_changed(self,c,msg):
        cb = self.on_enabled_status_changed_cb
        if cb is not None and msg[0] == self.sm_name:
            cb(msg[1])

    def on_enabled_status_changed(self,cb):
        self.on_enabled_status_changed_cb = cb

    def is_enableable(self):
        return self.sm_server.is_enableable(self.sm_name)
    
    def is_enabled(self):
        return self.sm_server.is_enabled(self.sm_name)

    def set_enabled(self,is_enabled):
        return self.sm_server.set_enabled(self.sm_name,is_enabled)

    def get_position(self):
        return self.sm_server.get_position(self.sm_name)

    def set_position(self,position):
        return self.sm_server.set_position(self.sm_name,position)

    def stop(self):
        self.sm_server.stop(self.sm_name,context=self.sm_server.context())
    



