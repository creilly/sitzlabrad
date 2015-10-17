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
from qtutils.labelwidget import LabelWidget

CHUNK = 50
RANGE = (-1000000,1000000)
CHUNKS_DIR = ['','Clients','Stepper Motor','chunks']
            
class StepperMotorWidget(QtGui.QWidget):
    def __init__(self,sm_client,chunk):
        QtGui.QWidget.__init__(self)
        self.sm_client = sm_client
        self.chunk = chunk
        self.init_widget()

    def init_widget(self):
        sm_client = self.sm_client
        chunk = self.chunk
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
            while True:
                if stop_check.isChecked():
                    stop_check.setCheckState(QtCore.Qt.Unchecked)
                    break
                current_position = yield sm_client.get_position()
                delta = requested_position - current_position
                if delta is 0:
                    break
                if abs(delta) < chunk:
                    yield sm_client.set_position(requested_position)
                    break
                else:
                    yield sm_client.set_position(
                        current_position + (
                            1 if delta > 0 else -1
                            ) * chunk
                        )
        set_position_button.clicked.connect(on_clicked)
        stop_check = QtGui.QCheckBox('stop')
        layout.addWidget(stop_check)

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
        registry = cxn.registry
        yield registry.cd(CHUNKS_DIR)
        _, chunk_keys = yield registry.dir()
        chunks = {}
        for chunk_key in chunk_keys:
            chunk = yield registry.get(chunk_key)
            chunks[chunk_key] = chunk
        sm_names = yield sm_server.get_stepper_motors()
        for name in sm_names:
            layout.addWidget(
                LabelWidget(
                    name,
                    StepperMotorWidget(
                        StepperMotorClient(name,sm_server),
                        chunks.get(name,CHUNK)
                    )
                )
            )
    def closeEvent(self,event):
        event.accept()
        if reactor.running():
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
