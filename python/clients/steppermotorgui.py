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
from qtutils.lockwidget import DeviceLockWidget
from functools import partial

RANGE = (-1000000,1000000)

class StepperMotorWidget(QtGui.QWidget):
    def __init__(self,sm_name):
        QtGui.QWidget.__init__(self)
        self.sm_name = sm_name
        self.init_widget()

    @inlineCallbacks
    def init_widget(self):        
        client = yield connectAsync()
        sm = client.stepper_motor
        yield sm.select_device(self.sm_name)
        
        layout = QtGui.QVBoxLayout()        
        self.setLayout(layout)
        
        position_label = QtGui.QLabel()
        layout.addWidget(position_label)
        
        def on_new_position(c,position):
            position_label.setNum(position)
        sm.on_new_position.connect(on_new_position)
        
        position_spin = QtGui.QSpinBox()
        layout.addWidget(position_spin)
        position_spin.setRange(*RANGE)
        sm.get_position().addCallback(position_label.setNum)
        set_position_button = QtGui.QPushButton('set position')
        layout.addWidget(set_position_button)
        
        @inlineCallbacks
        def on_set_position():
            is_busy = yield sm.is_busy()
            if is_busy:
                QtGui.QMessageBox.warning(self,'stepper motor busy','stepper motor is currently busy')
                returnValue(None)
            is_enabled = yield sm.is_enabled()
            if not is_enabled:
                QtGui.QMessageBox.warning(self,'stepper motor disabled','stepper motor is currently disabled')
                returnValue(None)
            requested_position = position_spin.value()            
            try:
                yield sm.set_position(requested_position)
            except Error, e:
                QtGui.QMessageBox.warning(self,'error',e.msg)
        set_position_button.clicked.connect(on_set_position)

        stop_button = QtGui.QPushButton('stop')
        stop_button.clicked.connect(sm.stop)
        layout.addWidget(stop_button)

        busy_label = QtGui.QLabel()
        def update_busy_status(is_busy):
            busy_label.setText(
                'busy' if is_busy else 'not busy'
            )
        sm.is_busy().addCallback(update_busy_status)
        def on_busy_status_changed(c,busy_status):
            update_busy_status(busy_status)
        sm.on_busy_status_changed.connect(on_busy_status_changed)
        layout.addWidget(busy_label)

        is_enableable = yield sm.is_enableable()
        if is_enableable:
            enabled_label = QtGui.QLabel()
            def update_enabled_status(is_enabled):
                enabled_label.setText(
                    'enabled' if is_enabled else 'disabled'
                )
            sm.is_enabled().addCallback(update_enabled_status)
            def on_enabled_status_changed(c,enabled_status):
                update_enabled_status(enabled_status)
            sm.on_enabled_status_changed.connect(on_enabled_status_changed)
            layout.addWidget(enabled_label)
            enable_button = QtGui.QPushButton('enable')
            enable_button.clicked.connect(partial(sm.set_enabled,True))
            layout.addWidget(enable_button)

            disable_button = QtGui.QPushButton('disable')
            disable_button.clicked.connect(partial(sm.set_enabled,False))
            layout.addWidget(disable_button)

        layout.addStretch()

        layout.addWidget(DeviceLockWidget(sm))

class StepperMotorGroupWidget(QtGui.QWidget):
    def __init__(self,sm_server):
        QtGui.QWidget.__init__(self)
        self.sm_server = sm_server
        self.init_widget()

    @inlineCallbacks
    def init_widget(self):        
        sm_server = self.sm_server
        layout = QtGui.QVBoxLayout()        
        self.setLayout(layout)
        cxn = yield connectAsync()
        sm_layout = QtGui.QHBoxLayout()

        layout.addLayout(sm_layout)

        sm_names = yield sm_server.get_devices()
        for name in sm_names:
            sm_layout.addWidget(
                LabelWidget(
                    name,
                    StepperMotorWidget(
                        name
                    )
                )
            )
            
    def closeEvent(self,event):
        if reactor.running:
            reactor.stop()
        event.accept()

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
