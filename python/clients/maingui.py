import sys
from PySide import QtGui, QtCore
if QtCore.QCoreApplication.instance() is None:
    app = QtGui.QApplication(sys.argv)
    import qt4reactor
    qt4reactor.install() 
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet import reactor
from labrad.wrappers import connectAsync
from voltmetergui import VoltmeterWidget
from steppermotorgui import StepperMotorGroupWidget
from delaygeneratorgui import DelayGeneratorGroupWidget
from labrad.support import mangle
from qtutils.labelwidget import LabelWidget

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
        man = client.manager
        widgets = {}
        servers = yield man.servers()
        server_names = []
        for tup in servers:
            id, name = tup
            server_names.append(name)
        for server_name,server_widget in WIDGETS.items():
            if server_name in server_names:
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
        def on_disconnect(c,msg):
            server_name = msg[1]
            if server_name not in WIDGETS:
                return
            widget = widgets.pop(server_name)
            layout.removeWidget(widget)
            widget.deleteLater()
        def on_connect(c,msg):
            server_name = msg[1]
            if server_name not in WIDGETS:
                return
            widget = LabelWidget(
                server_name,
                WIDGETS[server_name](client.servers[server_name])
            )
            widgets[server_name] = widget
            layout.addWidget(widget)
        yield man.subscribe_to_named_message('Server Connect', 55443322, True)
        yield man.subscribe_to_named_message('Server Disconnect', 66554433, True)
        man.addListener(on_connect, source=man.ID, ID=55443322)
        man.addListener(on_disconnect, source=man.ID, ID=66554433)

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
