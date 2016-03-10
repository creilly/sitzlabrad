import sys
from PySide import QtGui, QtCore
if QtCore.QCoreApplication.instance() is None:
    app = QtGui.QApplication(sys.argv)
    import qt4reactor
    qt4reactor.install() 
from twisted.internet.defer import Deferred, inlineCallbacks, returnValue
from twisted.internet import reactor
from labrad.wrappers import connectAsync
from labrad.types import Error
from qtutils.labelwidget import LabelWidget
from functools import partial
import numpy as np

class AnalogOutputWidget(QtGui.QWidget):
    def __init__(self,ao_server):
        QtGui.QWidget.__init__(self)
        self.ao_server = ao_server
        self.init_widget()

    @inlineCallbacks
    def init_widget(self):
        ao = self.ao_server
        channels = yield ao.get_channels()
        units = {}
        for channel in channels:
            unit = yield ao.get_units(channel)
            units[channel] = unit
        layout = QtGui.QHBoxLayout()
        self.setLayout(layout)
        labels = {
            channel:QtGui.QLabel() for channel in channels
        }
        def button_clicked(channel,spin):
            def set_value():
                ao.set_value(channel,spin.value())
            return set_value
        for channel in channels:
            channel_layout = QtGui.QVBoxLayout()
            channel_layout.addWidget(labels[channel])
            spin = QtGui.QDoubleSpinBox()
            spin.setSuffix(units[channel])
            channel_layout.addWidget(spin)
            min_value, max_value = yield ao.get_range(channel)
            spin.setRange(min_value,max_value)
            decimals = int(
                np.log10(
                    2**16/(max_value-min_value)
                ) + 1
            )
            spin.setDecimals(
                decimals if decimals > 0 else 0
            )
            button = QtGui.QPushButton('set')
            button.clicked.connect(
                button_clicked(channel,spin)
            )
            channel_layout.addWidget(button)
            layout.addWidget(
                LabelWidget(
                    channel,
                    channel_layout
                )
            )
        def on_new_value(channel,value):
            labels[channel].setText(
                '%f %s' % (value,units[channel])
            )
        ao.on_new_value.connect(
            lambda context, data:
            on_new_value(*data)
        )
        for channel in channels:
            value = yield ao.get_value(channel)
            on_new_value(channel,value)

    def closeEvent(self,event):
        if reactor.running:
            reactor.stop()
        event.accept()

if __name__ == '__main__':
    @inlineCallbacks
    def main():
        cxn = yield connectAsync()
        ao_widget = AnalogOutputWidget(cxn.analog_output)
        container.append(ao_widget)
        ao_widget.show()
    container = []
    reactor.callWhenRunning(main)
    reactor.run()
