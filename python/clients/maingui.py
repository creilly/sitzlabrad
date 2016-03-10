import sys
from PySide import QtGui, QtCore
if QtCore.QCoreApplication.instance() is None:
    app = QtGui.QApplication(sys.argv)
    import qt4reactor
    qt4reactor.install()
from aogui import AnalogOutputWidget
from voltmetergui import VoltmeterWidget
from steppermotorgui import StepperMotorGroupWidget
from delaygeneratorgui import DelayGeneratorGroupWidget
from labrad.support import mangle
from qtutils.labelwidget import LabelWidget
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet import reactor
from labrad.wrappers import connectAsync
from connectionmanager import ConnectionManager
from functools import partial

WIDGETS = {
    'Voltmeter':VoltmeterWidget,
    'Stepper Motor':StepperMotorGroupWidget,
    'Delay Generator':DelayGeneratorGroupWidget,
    'Analog Output':AnalogOutputWidget
}
class MainWidget(QtGui.QTabWidget):
    def __init__(self,client):
        QtGui.QTabWidget.__init__(self)
        self.client = client
        self.init_gui()

    @inlineCallbacks
    def init_gui(self):
        client = self.client
        connection_manager = ConnectionManager(client.manager)
        widgets = {}
        connected_servers = yield connection_manager.get_connected_servers()
        servers = yield self.client.manager.servers()
        def on_disconnect(server_name):
            widget = widgets.pop(server_name)
            self.removeTab(
                self.indexOf(widget)
            )
            widget.deleteLater()
        @inlineCallbacks
        def on_connect(server_name):
            yield client.refresh()
            widget_class = WIDGETS[server_name]
            server = client.servers[server_name]
            widget = widget_class(server)
            widgets[server_name] = widget
            self.addTab(widget,server_name)
        for server_name,server_widget in WIDGETS.items():
            connection_manager.on_server_connect(
                server_name,
                partial(on_connect,server_name)
            )
            connection_manager.on_server_disconnect(
                server_name,
                partial(on_disconnect,server_name)
            )
            if server_name in connected_servers:
                widget = server_widget(
                    client.servers[server_name]
                )
                widgets[server_name] = widget
                self.addTab(widget,server_name)

    def closeEvent(self,event):
        event.accept()
        reactor.stop()

if __name__ == '__main__':
    @inlineCallbacks
    def main():
        cxn = yield connectAsync()        
        main_widget = MainWidget(cxn)
        container.append(main_widget)
        main_widget.show()
    container = []
    reactor.callWhenRunning(main)
    reactor.run()
