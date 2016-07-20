from twisted.internet.defer import inlineCallbacks

class StepperMotorClient:
    LOCKED, HAS_LOCK, UNLOCKED = 0,1,2
    def __init__(self,sm_name,sm_server):
        self.sm_name = sm_name
        self.sm_server = sm_server
        sm_server.on_new_position.connect(
            self._on_new_position
        )
        sm_server.on_busy_status_changed.connect(
            self._on_busy_status_changed
        )
        sm_server.on_enabled_status_changed.connect(
            self._on_enabled_status_changed
        )
        sm_server.on_setting_locked.connect(
            self._on_setting_locked
        )
        sm_server.on_setting_locked.connect(
            self._on_setting_locked
        )
        sm_server.on_setting_unlocked.connect(
            self._on_setting_unlocked
        )
        self.on_new_position_cb = None
        self.on_busy_status_changed_cb = None
        self.on_enabled_status_changed_cb = None
        self.on_locked_cb = None
        self.on_unlocked_cb = None

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

    def is_locked(self):
        return self.sm_server.is_setting_locked(self.sm_server.set_position.ID)

    def has_lock(self):
        return self.sm_server.has_setting_lock(self.sm_server.set_position.ID)

    def _on_setting_locked(self,c,msg):
        setting_id = msg[0]
        if setting_id == self.sm_server.set_position.ID:
            if self.on_locked_cb is not None:
                self.on_locked_cb()
            
    def _on_setting_unlocked(self,c,msg):
        setting_id = msg
        if setting_id == self.sm_server.set_position.ID:
            if self.on_unlocked_cb is not None:
                self.on_unlocked_cb()

    def on_locked(self,cb):
        self.on_locked_cb = cb

    def on_unlocked(self,cb):
        self.on_unlocked_cb = cb

    def lock(self):
        return self.sm_server.lock_setting(self.sm_server.set_position.ID)

    def unlock(self):
        return self.sm_server.unlock_setting(self.sm_server.set_position.ID)

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
        self.sm_server.stop(
            self.sm_name,
            context=self.sm_server.context()
        )
    
    



