import sys
from PySide import QtGui, QtCore
if QtCore.QCoreApplication.instance() is None:
    app = QtGui.QApplication(sys.argv)
    import qt4reactor
    qt4reactor.install() 
from twisted.internet.defer import Deferred, inlineCallbacks, returnValue
from twisted.internet import reactor
from steppermotorclient import StepperMotorClient
from labrad.wrappers import connectAsync
from labrad.types import Error
from qtutils.labelwidget import LabelWidget
from functools import partial

RANGE = (-1000000,1000000)
            
class StepperMotorWidget(QtGui.QWidget):
    def __init__(self,sm_client):
        QtGui.QWidget.__init__(self)
        self.sm_client = sm_client
        self.init_widget()

    def init_widget(self):
        sm_client = self.sm_client
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        position_label = QtGui.QLabel()
        layout.addWidget(position_label)
        sm_client.on_new_position(position_label.setNum)
        position_spin = QtGui.QSpinBox()
        layout.addWidget(position_spin)
        position_spin.setRange(*RANGE)
        sm_client.get_position().addCallback(position_label.setNum)
        set_position_button = QtGui.QPushButton('set position')
        layout.addWidget(set_position_button)
        @inlineCallbacks
        def on_clicked():
            requested_position = position_spin.value()
            try:
                yield sm_client.set_position(requested_position)
            except Error, e:
                QtGui.QMessageBox.warning(self,'error',str(e))
        set_position_button.clicked.connect(on_clicked)
        stop_button = QtGui.QPushButton('stop')
        stop_button.clicked.connect(sm_client.stop)
        layout.addWidget(stop_button)

        busy_label = QtGui.QLabel()
        def update_busy_status(is_busy):
            busy_label.setText(
                'busy' if is_busy else 'not busy'
            )
        sm_client.is_busy().addCallback(update_busy_status)
        sm_client.on_busy_status_changed(update_busy_status)
        layout.addWidget(busy_label)

        def on_is_enableable(is_enableable):
            if is_enableable:
                enabled_label = QtGui.QLabel()
                def update_enabled_status(is_enabled):
                    enabled_label.setText(
                        'enabled' if is_enabled else 'disabled'
                    )
                sm_client.is_enabled().addCallback(update_enabled_status)
                sm_client.on_enabled_status_changed(update_enabled_status)
                layout.addWidget(enabled_label)
                enable_button = QtGui.QPushButton('enable')
                enable_button.clicked.connect(partial(sm_client.set_enabled,True))
                layout.addWidget(enable_button)

                disable_button = QtGui.QPushButton('disable')
                disable_button.clicked.connect(partial(sm_client.set_enabled,False))
                layout.addWidget(disable_button)
        sm_client.is_enableable().addCallback(on_is_enableable)

        layout.addStretch()
        

class StepperMotorGroupWidget(QtGui.QWidget):
    def __init__(self,sm_server):
        QtGui.QWidget.__init__(self)
        self.sm_server = sm_server
        self.init_widget()

    @inlineCallbacks
    def init_widget(self):
        sm_server = self.sm_server
        layout = QtGui.QHBoxLayout()
        self.setLayout(layout)
        cxn = yield connectAsync()
        sm_names = yield sm_server.get_stepper_motors()
        for name in sm_names:
            layout.addWidget(
                LabelWidget(
                    name,
                    StepperMotorWidget(
                        StepperMotorClient(name,sm_server)
                    )
                )
            )
    def closeEvent(self,event):
        event.accept()
        if reactor.running:
            reactor.stop()

if __name__ == '__main__':
    @inlineCallbacks
    def main():
        cxn = yield connectAsync()
        sm_widget = StepperMotorGroupWidget(cxn.stepper_motor)
        container.append(sm_widget)
        sm_widget.show()
    container = []
    reactor.callWhenRunning(main)
    reactor.run()
