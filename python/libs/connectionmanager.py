from twisted.internet.defer import inlineCallbacks, returnValue
ON_SERVER_CONNECT = 55443322
ON_SERVER_DISCONNECT = 66554433
class ConnectionManager:
    def __init__(self,manager):
        self.manager = manager
        self.connect_callbacks = {}
        self.disconnect_callbacks = {}
        manager.subscribe_to_named_message('Server Connect', ON_SERVER_CONNECT, True)
        manager.subscribe_to_named_message('Server Disconnect', ON_SERVER_DISCONNECT, True)
        manager.addListener(self._on_server_connect, source=manager.ID, ID=ON_SERVER_CONNECT)
        manager.addListener(self._on_server_disconnect, source=manager.ID, ID=ON_SERVER_DISCONNECT)

    @inlineCallbacks
    def get_connected_servers(self):
        servers = []
        server_tups = yield self.manager.servers()
        for id, server in server_tups:
            servers.append(server)
        returnValue(servers)

    def _on_server_connect(self,_,msg):
        server = msg[1]
        if server in self.connect_callbacks:         
            self.connect_callbacks[server]()
        
    def _on_server_disconnect(self,_,msg):
        server = msg[1]
        if server in self.disconnect_callbacks:            
            self.disconnect_callbacks[server]()
        
    def on_server_connect(self,server,callback):
        if callback is not None:
            self.connect_callbacks[server]=callback
        else:
            self.connect_callbacks.pop(server)

    def on_server_disconnect(self,server,callback):
        if callback is not None:
            self.disconnect_callbacks[server]=callback
        else:
            self.disconnect_callbacks.pop(server)

