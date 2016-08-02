import sys
from PySide import QtGui, QtCore
if QtCore.QCoreApplication.instance() is None:
    app = QtGui.QApplication(sys.argv)
    import qt4reactor
    qt4reactor.install() 
from twisted.internet.defer import Deferred, inlineCallbacks, returnValue
from twisted.internet import reactor
from labrad.wrappers import connectAsync
from qtutils.labelwidget import LabelWidget
from qtutils.labraderror import catch_labrad_error
from qtutils.lockwidget import DeviceLockWidget
from twisted.internet.defer import inlineCallbacks

RANGE = (1,10000000)
            
class DelayGeneratorWidget(QtGui.QWidget):
    def __init__(self,dg_name):
        QtGui.QWidget.__init__(self)
        self.dg_name = dg_name
        self.init_gui()

    @inlineCallbacks
    def init_gui(self):
        layout = QtGui.QVBoxLayout()
        client = yield connectAsync()
        dg_server = client.delay_generator
        yield dg_server.select_device(self.dg_name)
        self.setLayout(layout)
        delay_label = QtGui.QLabel()
        layout.addWidget(delay_label)
        dg_server.on_new_delay.connect(lambda c, delay: delay_label.setNum(delay))
        delay_spin = QtGui.QSpinBox()
        layout.addWidget(delay_spin)
        delay_spin.setRange(*RANGE)
        dg_server.get_delay().addCallback(delay_label.setNum)
        set_delay_button = QtGui.QPushButton('set delay')
        layout.addWidget(set_delay_button)
        layout.addWidget(DeviceLockWidget(dg_server))
        def on_clicked():
            catch_labrad_error(
                self,
                dg_server.set_delay(delay_spin.value())
            )                
        set_delay_button.clicked.connect(on_clicked)
        

class DelayGeneratorGroupWidget(QtGui.QWidget):
    def __init__(self,dg_server):
        QtGui.QWidget.__init__(self)
        layout = QtGui.QHBoxLayout()
        self.setLayout(layout)
        def on_dg_names(dg_names):
            for dg_name in dg_names:  
                layout.addWidget(
                    LabelWidget(
                        dg_name,
                        DelayGeneratorWidget(dg_name)
                    )
                )
        dg_server.get_devices().addCallback(on_dg_names)
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
