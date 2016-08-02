from twisted.internet.defer import inlineCallbacks, returnValue
from PySide import QtGui
from labelwidget import LabelWidget
from labraderror import catch_labrad_error
from functools import partial
from labrad.types import Error

class LockWidget(LabelWidget):
    def __init__(self,server,setting_id,setting_name):        
        layout = QtGui.QHBoxLayout()

        label = QtGui.QLabel()
        layout.addWidget(label)

        layout.addStretch()

        lock_button = QtGui.QPushButton('lock')
        layout.addWidget(lock_button)

        unlock_button = QtGui.QPushButton('unlock')
        layout.addWidget(unlock_button)

        @inlineCallbacks
        def update_lock_state(is_locked):
            label_prefix = 'status'
            if is_locked:
                success, has_lock = yield catch_labrad_error(
                    self,
                    server.has_setting_lock(setting_id)                    
                )
                if not success:                    
                    server.is_setting_locked(setting_id).addCallback(update_lock_state)
                    returnValue(None)                
                label_suffix = 'has lock' if has_lock else 'locked'
            else:
                label_suffix = 'unlocked'
            label.setText(label_prefix + ': ' + label_suffix)

        def on_setting_lock_state_changed(
                is_locked,
                context,
                changed_id
        ):
            if changed_id == setting_id:
                update_lock_state(is_locked)

        for message, is_locked in (
                (
                    server.on_setting_locked,
                    True
                ),
                (
                    server.on_setting_unlocked,
                    False
                )
        ):
            message.connect(
                partial(
                    on_setting_lock_state_changed,
                    is_locked
                )
            )
        def set_lock_state(locking):
            catch_labrad_error(
                self,
                server.lock_setting(setting_id)
                if locking else
                server.unlock_setting(setting_id)
            )
        for button, locking in (
                (
                    lock_button,
                    True
                ),
                (
                    unlock_button,
                    False
                )
        ):
            button.clicked.connect(
                partial(
                    set_lock_state,
                    locking
                )
            )
        server.is_setting_locked(setting_id).addCallback(update_lock_state)

        LabelWidget.__init__(self,setting_name,layout)

class DeviceLockWidget(LabelWidget):
    def __init__(self,server):
        lock_layout = QtGui.QHBoxLayout()
        
        lock_label = QtGui.QLabel()
        lock_layout.addWidget(lock_label)

        lock_layout.addStretch()
        
        lock_button = QtGui.QPushButton('lock')
        lock_layout.addWidget(lock_button)
        unlock_button = QtGui.QPushButton('unlock')
        lock_layout.addWidget(unlock_button)

        @inlineCallbacks
        def update_lock_status(is_locked):
            prefix = 'status'
            if is_locked:
                success, has_lock = yield catch_labrad_error(
                    self,
                    server.has_lock()
                )
                if not success:
                    is_locked = yield server.is_locked()
                    update_lock_status(is_locked)
                    returnValue(None)
                suffix = 'has lock' if has_lock else 'locked'
            else:
                suffix = 'unlocked'
            lock_label.setText(prefix + ': ' + suffix)
                
        def on_locked_status_changed(is_locked,_,__):
            update_lock_status(is_locked)

        for signal, is_locked in (
                (
                    server.on_locked,
                    True
                ),
                (
                    server.on_unlocked,
                    False
                )
        ):
            signal.connect(partial(on_locked_status_changed,is_locked))

        server.is_locked().addCallback(update_lock_status)

        def set_lock(is_locking):
            catch_labrad_error(
                self,
                server.lock() if is_locking else server.unlock()
            )
            
        for button, is_locking in (
                (
                    lock_button,
                    True
                ),
                (
                    unlock_button,
                    False
                )
        ):
            button.clicked.connect(partial(set_lock,is_locking))

        LabelWidget.__init__(self,'lock',lock_layout)
