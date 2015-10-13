import sys
from PySide import QtGui, QtCore
if QtCore.QCoreApplication.instance() is None:
    app = QtGui.QApplication(sys.argv)
    import qt4reactor
    qt4reactor.install() 
from voltmetergui import VoltmeterWidget
from steppermotorgui import StepperMotorGroupWidget
from delaygeneratorgui import DelayGeneratorGroupWidget
from labrad.support import mangle
from qtutils.labelwidget import LabelWidget
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet import reactor
from labrad.wrappers import connectAsync
from connectionmanager import ConnectionManager

WIDGETS = {
    'Voltmeter':VoltmeterWidget,
    'Stepper Motor':StepperMotorGroupWidget,
    'Delay Generator':DelayGeneratorGroupWidget
}
class MainWidget(QtGui.QWidget):
    def __init__(self,client):
        QtGui.QWidget.__init__(self)
        self.client = client
        self.init_gui()

    @inlineCallbacks
    def init_gui(self):
        layout = QtGui.QHBoxLayout()
        self.setLayout(layout)
        client = self.client
        connection_manager = ConnectionManager(client.manager)
        widgets = {}
        server_names = yield connection_manager.get_connected_servers()
        def on_disconnect(server_name):
            widget = widgets.pop(server_name)
            layout.removeWidget(widget)
            widget.deleteLater()
        def on_connect(server_name):
            widget = LabelWidget(
                WIDGETS[server_name](client.servers[server_name])
            )
            widgets[server_name] = widget
            layout.addWidget(widget)
        for server_name,server_widget in WIDGETS.items():
            connection_manager.on_server_connect(server_name, lambda: on_connect(server_name))
            connection_manager.on_server_disconnect(server_name, lambda: on_disconnect(server_name))
            if server in server_names:
                widget = LabelWidget(
                    server_name,
                    server_widget(
                        client.servers[
                            mangle(
                                server_name
                            )
                        ]
                    )
                )
                widgets[server_name] = widget
                layout.addWidget(widget)


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
