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
from qtutils.lockwidget import DeviceLockWidget
from qtutils.labraderror import catch_labrad_error

class AnalogOutputWidget(QtGui.QWidget):
    def __init__(self,channel_name):
        QtGui.QWidget.__init__(self)
        self.channel_name = channel_name
        self.init_widget()

    @inlineCallbacks
    def init_widget(self):
        client = yield connectAsync()
        ao = client.analog_output
        yield ao.select_device(self.channel_name)

        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)

        value_label = QtGui.QLabel()
        layout.addWidget(value_label)
        
        units = yield ao.get_units()
        
        spin = QtGui.QDoubleSpinBox()
        spin.setSuffix(units)
        layout.addWidget(spin)
        
        min_value, max_value = yield ao.get_range()
        spin.setRange(min_value,max_value)
        decimals = int(
            np.log10(
                2**16/(max_value-min_value)
            ) + 1
        )
        spin.setDecimals(
            decimals if decimals > 0 else 0
        )
        
        set_button = QtGui.QPushButton('set')
        def on_set_clicked():
            catch_labrad_error(self,ao.set_value(spin.value()))
        set_button.clicked.connect(on_set_clicked)
        
        layout.addWidget(set_button)
            
        def on_new_value(value):
            value_label.setText(
                '%f %s' % (value,units)
            )
        ao.on_new_value.connect(
            lambda context, value:
            on_new_value(value)
        )
        value = yield ao.get_value()
        on_new_value(value)

        layout.addWidget(DeviceLockWidget(ao))

class AnalogOutputGroupWidget(QtGui.QWidget):
    def __init__(self,ao):
        QtGui.QWidget.__init__(self)
        self.ao = ao
        self.init_widget()

    @inlineCallbacks
    def init_widget(self):
        layout = QtGui.QHBoxLayout()
        self.setLayout(layout)        
        ao = self.ao
        channel_names = yield ao.get_devices()
        for channel_name in channel_names:
            layout.addWidget(
                LabelWidget(
                    channel_name,
                    AnalogOutputWidget(channel_name)
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
        ao_widget = AnalogOutputGroupWidget(cxn.analog_output)
        container.append(ao_widget)
        ao_widget.show()
    container = []
    reactor.callWhenRunning(main)
    reactor.run()
