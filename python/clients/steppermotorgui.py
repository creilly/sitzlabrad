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
from qtutils.lockwidget import LockWidget
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
        def on_set_position():
            is_busy = yield sm_client.is_busy()
            if is_busy:
                QtGui.QMessageBox.warning(self,'stepper motor busy','stepper motor is currently busy')
                returnValue(None)
            is_enabled = yield sm_client.is_enabled()
            if not is_enabled:
                QtGui.QMessageBox.warning(self,'stepper motor disabled','stepper motor is currently disabled')
                returnValue(None)
            requested_position = position_spin.value()            
            try:
                yield sm_client.set_position(requested_position)
            except Error, e:
                QtGui.QMessageBox.warning(self,'error',e.msg)
        set_position_button.clicked.connect(on_set_position)

        lock_label = QtGui.QLabel()
        @inlineCallbacks
        def update_lock_state(is_locked):
            if is_locked:
                try:
                    has_lock = yield sm_client.has_lock()
                except Error, e:
                    QtGui.QMessageBox.warning(self,'error',e.msg)
                    sm_client.is_locked().addCallback(update_lock_state)
                    returnValue(None)
                lock_label.setText('has lock' if has_lock else 'locked')
            else:
                lock_label.setText('unlocked')
        sm_client.on_locked(
            partial(
                update_lock_state,
                True
            )
        )
        sm_client.on_unlocked(
            partial(
                update_lock_state,
                False
            )
        )
        layout.addWidget(lock_label)
        sm_client.is_locked().addCallback(update_lock_state)

        @inlineCallbacks
        def change_lock_state(locking):
            try:
                if locking:
                    yield sm_client.lock()
                else:
                    yield sm_client.unlock()
            except Error, e:
                QtGui.QMessageBox.warning(self,'error',e.msg)
        
        lock_button = QtGui.QPushButton('lock')
        lock_button.clicked.connect(partial(change_lock_state,True))
        layout.addWidget(lock_button)
        
        unlock_button = QtGui.QPushButton('unlock')
        unlock_button.clicked.connect(partial(change_lock_state,False))
        layout.addWidget(unlock_button)
        
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
        layout = QtGui.QVBoxLayout()        
        self.setLayout(layout)
        cxn = yield connectAsync()
        sm_layout = QtGui.QHBoxLayout()

        layout.addLayout(sm_layout)

        sm_names = yield sm_server.get_stepper_motors()
        for name in sm_names:
            sm_layout.addWidget(
                LabelWidget(
                    name,
                    StepperMotorWidget(
                        StepperMotorClient(name,sm_server)
                    )
                )
            )
        layout.addWidget(LockWidget(sm_server,sm_server.set_position,'set position'))
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
