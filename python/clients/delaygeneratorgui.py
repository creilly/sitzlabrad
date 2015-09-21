import sys
from PySide import QtGui, QtCore
if QtCore.QCoreApplication.instance() is None:
    app = QtGui.QApplication(sys.argv)
    import qt4reactor
    qt4reactor.install() 
from twisted.internet.defer import Deferred, inlineCallbacks, returnValue
from twisted.internet import reactor
from delaygeneratorclient import DelayGeneratorClient
from labrad.wrappers import connectAsync
from qtutils.labelwidget import LabelWidget

RANGE = (1,10000000)
            
class DelayGeneratorWidget(QtGui.QWidget):
    def __init__(self,dg_client):
        QtGui.QWidget.__init__(self)
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        delay_label = QtGui.QLabel()
        layout.addWidget(delay_label)
        dg_client.on_new_delay(delay_label.setNum)
        delay_spin = QtGui.QSpinBox()
        layout.addWidget(delay_spin)
        delay_spin.setRange(*RANGE)
        dg_client.get_delay().addCallback(delay_label.setNum)
        set_delay_button = QtGui.QPushButton('set delay')
        layout.addWidget(set_delay_button)
        def on_clicked():
            dg_client.set_delay(delay_spin.value())
        set_delay_button.clicked.connect(on_clicked)

class DelayGeneratorGroupWidget(QtGui.QWidget):
    def __init__(self,dg_server):
        QtGui.QWidget.__init__(self)
        layout = QtGui.QHBoxLayout()
        self.setLayout(layout)
        @inlineCallbacks
        def on_delay_generators(dg_ids):
            for id in dg_ids:  
                name = yield dg_server.get_name(id)
                layout.addWidget(
                    LabelWidget(
                        name,
                        DelayGeneratorWidget(
                            DelayGeneratorClient(id,dg_server)
                        )
                    )
                )
        dg_server.get_delay_generators().addCallback(on_delay_generators)
    def closeEvent(self,event):
        event.accept()
        if reactor.running:
            reactor.stop()

if __name__ == '__main__':
    @inlineCallbacks
    def main():
        cxn = yield connectAsync()        
        dg_widget = DelayGeneratorGroupWidget(cxn.delay_generator)
        container.append(dg_widget)
        dg_widget.show()
    container = []
    reactor.callWhenRunning(main)
    reactor.run()
