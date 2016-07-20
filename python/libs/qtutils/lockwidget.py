from labelwidget import LabelWidget
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
                try:
                    has_lock = yield server.has_setting_lock(setting_id)
                except Error, e:
                    QtGui.QMessageBox.warning(
                        self,
                        'error',
                        e.msg
                    )
                    server.is_setting_locked(setting_id).addCallback(update_lock_state)
                    returnValue(None)
                label_suffix = 'has lock' if has_lock else 'locked'
            else:
                label_suffix = 'unlocked'
            label.setText(label_prefix + ': ' + label_suffix)

        def on_setting_lock_state_changed(
                is_locked,
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
            try:
                if locking:
                    yield server.lock_setting(setting_id)
                else:
                    yield server.unlock_setting(setting_id)
            except Error, e:
                QtGui.QMessageBox.warning(self,'error',e.msg)

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

