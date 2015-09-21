MESSAGE_ID = 210
class DelayGeneratorClient:
    def __init__(self,dg_id,dg_server):
        self.dg_id = dg_id
        self.dg_server = dg_server
        self.callback = None
        dg_server.on_new_delay(MESSAGE_ID)
        dg_server.addListener(
            listener=self._on_new_delay,source=None,ID=MESSAGE_ID
            )
    def _on_new_delay(self,c,msg):
        if self.callback is not None and msg[0] == self.dg_id:
            self.callback(msg[1])
    def on_new_delay(self,cb):
        self.callback = cb

    def get_delay(self):
        return self.dg_server.get_delay(self.dg_id)

    def set_delay(self,delay):
        return self.dg_server.set_delay(self.dg_id,delay)
    
