import sys
from PySide import QtGui, QtCore
if QtCore.QCoreApplication.instance() is None:
    app = QtGui.QApplication(sys.argv)
    import qt4reactor
    qt4reactor.install() 
from twisted.internet.defer import Deferred, inlineCallbacks, returnValue
from twisted.internet import reactor
from labrad.wrappers import connectAsync
from pyqtgraph import PlotWidget

CHANNEL = 999
TRACE_SIZE = 150
class VoltmeterWidget(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.init_widget()
    @inlineCallbacks
    def init_widget(self):
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        list_widget = QtGui.QListWidget()
        layout.addWidget(list_widget)
        cxn = yield connectAsync()
        vm = cxn.voltmeter
        channels = yield vm.get_channels()
        traces = {
            channel:[0]*TRACE_SIZE for channel in channels
            }
        dialogs = {
            }
        for channel in channels:
            list_item = QtGui.QListWidgetItem(channel)
            list_item.setData(CHANNEL,channel)
            list_widget.addItem(list_item)
        def on_double_clicked(item):
            channel = item.data(CHANNEL)
            if channel in dialogs:
                dialogs[channel].activateWindow()
            else:   
                dialog = ChannelWidget(channel,traces[channel])
                dialogs[channel] = dialog
                def on_finished(_):
                    dialogs.pop(channel)
                    self.activateWindow()
                dialog.finished.connect(on_finished)
                dialog.show()
        list_widget.itemDoubleClicked.connect(on_double_clicked)
        run_check = QtGui.QCheckBox()
        layout.addWidget(run_check)
        @inlineCallbacks
        def get_samples():
            packet = vm.packet()
            for channel in channels:
                packet.get_sample(channel,key=channel)
            samples = yield packet.send()
            for list_item in [
                list_widget.item(index)
                for index in range(list_widget.count())                
                ]:
                channel = list_item.data(CHANNEL)
                sample = samples[channel]
                trace = traces[channel]
                trace.pop()
                trace.insert(0,sample)
                list_item.setText('%s\t%.2f'%(channel,sample))
            if run_check.isChecked():
                get_samples()            
            for dialog in dialogs.values():
                dialog.update_plot()
        def on_run_state_changed(state):
            if state:
                get_samples()
        run_check.stateChanged.connect(on_run_state_changed)
        
    def closeEvent(self,event):
        event.accept()
        reactor.stop()

class ChannelWidget(QtGui.QDialog):
    def __init__(self,channel,trace):
        QtGui.QDialog.__init__(self)
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        plot_widget = PlotWidget(
            title='%s trace' % channel, 
            labels={'left':'volts'}
                    )
        layout.addWidget(plot_widget)
        plot = plot_widget.plot(trace)
        self.plot = plot
        self.trace = trace
    def update_plot(self):
        self.plot.setData(self.trace)
if __name__ == '__main__':
    def main():
        vm_widget = VoltmeterWidget()
        container.append(vm_widget)
        vm_widget.show()
    container = []
    reactor.callWhenRunning(main)
    reactor.run()
