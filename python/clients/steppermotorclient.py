MESSAGE_ID = 210
class StepperMotorClient:
    def __init__(self,sm_name,sm_server):
        self.sm_name = sm_name
        self.sm_server = sm_server
        self.callback = None
        sm_server.on_new_position(MESSAGE_ID)
        sm_server.addListener(
            listener=self._on_new_position,source=None,ID=MESSAGE_ID
            )
    def _on_new_position(self,c,msg):
        if self.callback is not None and msg[0] == self.sm_name:
            self.callback(msg[1])
    def on_new_position(self,cb):
        self.callback = cb

    def get_position(self):
        return self.sm_server.get_position(self.sm_name)

    def set_position(self,position):
        return self.sm_server.set_position(self.sm_name,position)
    
