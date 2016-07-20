import sys
from PySide import QtGui, QtCore
if QtCore.QCoreApplication.instance() is None:
    app = QtGui.QApplication(sys.argv)
    import qt4reactor
    qt4reactor.install()
from pyqtgraph import PlotWidget
from twisted.internet.defer import Deferred, inlineCallbacks, returnValue
from twisted.internet import reactor
from labrad.wrappers import connectAsync
from qtutils.labelwidget import LabelWidget
from qtutils.lockwidget import LockWidget
CHANNEL = 999
TRACE_SIZE = 150
class VoltmeterWidget(QtGui.QWidget):
    def __init__(self,vm_server):
        QtGui.QWidget.__init__(self)
        self.vm_server = vm_server
        self.init_widget()
    @inlineCallbacks
    def init_widget(self):
        vm = self.vm_server
        client = yield connectAsync()
        layout = QtGui.QHBoxLayout()
        self.setLayout(layout)

        active_layout = QtGui.QVBoxLayout()
        layout.addLayout(active_layout)
        
        active_channels_widget = QtGui.QListWidget()
        active_layout.addWidget(
            LabelWidget(
                'active channels',
                active_channels_widget
            )
        )        

        active_controls_layout = QtGui.QHBoxLayout()
        active_layout.addLayout(active_controls_layout)
        
        remove_button = QtGui.QPushButton('remove')
        active_controls_layout.addWidget(remove_button)

        active_controls_layout.addStretch()

        inactive_layout = QtGui.QVBoxLayout()
        layout.addLayout(inactive_layout)

        inactive_channels_widget = QtGui.QListWidget()
        inactive_layout.addWidget(
            LabelWidget(
                'inactive channels',
                inactive_channels_widget
            )
        )

        inactive_controls_layout = QtGui.QHBoxLayout()
        inactive_layout.addLayout(inactive_controls_layout)

        add_button = QtGui.QPushButton('add')
        inactive_controls_layout.addWidget(add_button)

        inactive_controls_layout.addStretch()

        general_controls_layout = QtGui.QVBoxLayout()
        layout.addLayout(general_controls_layout)

        run_layout = QtGui.QHBoxLayout()
        general_controls_layout.addLayout(run_layout)
        run_check = QtGui.QCheckBox('run')
        run_layout.addWidget(run_check)
        run_layout.addStretch()

        sampling_duration_layout = QtGui.QHBoxLayout()
        general_controls_layout.addLayout(sampling_duration_layout)
        sampling_duration_label = QtGui.QLabel()
        sampling_duration_layout.addWidget(sampling_duration_label)
        sampling_duration_spin = QtGui.QSpinBox()
        sampling_duration_layout.addWidget(sampling_duration_spin)
        sampling_duration_spin.setRange(1,100000)
        sampling_duration_spin.setSuffix('ms')

        sampling_duration_button = QtGui.QPushButton('set')
        sampling_duration_layout.addWidget(sampling_duration_button)
        sampling_duration_layout.addStretch()

        triggering_layout = QtGui.QHBoxLayout()
        general_controls_layout.addLayout(triggering_layout)
        triggering_label = QtGui.QLabel()
        triggering_layout.addWidget(triggering_label)
        triggering_button = QtGui.QPushButton('toggle triggering')
        triggering_layout.addWidget(triggering_button)
        triggering_layout.addStretch()

        locks_layout = QtGui.QVBoxLayout()
        general_controls_layout.addWidget(
            LabelWidget(
                'locks',
                locks_layout
            )
        )
        locks = (
            (
                'active channels',vm.set_active_channels.ID
            ),
            (
                'sampling duration',vm.set_sampling_duration.ID
            ),
            (
                'triggering',vm.set_triggering.ID
            )
        )
        for setting_name, setting_id in locks:
            locks_layout.addWidget(LockWidget(vm,setting_id,setting_name))
        
        active_channels = yield vm.get_active_channels()
        available_channels = yield vm.get_available_channels()

        font = QtGui.QListWidgetItem().font()
        bold_font = QtGui.QFont(font)
        bold_font.setWeight(QtGui.QFont.Bold)

        units_d = {} 

        for channel in available_channels:
            units = yield vm.get_units(channel)
            units_d[channel] = units
            list_item = QtGui.QListWidgetItem(channel)
            list_item.setFont(font)                
            list_item.setData(CHANNEL,channel)
            (
                active_channels_widget
                if channel in active_channels else
                inactive_channels_widget
            ).addItem(list_item)
        
        def update_channels(active_channels):
            acw = active_channels_widget
            icw = inactive_channels_widget
            active_items = [
                acw.item(index)
                for index in range(acw.count())
            ]
            inactive_items = [
                icw.item(index)
                for index in range(icw.count())
            ]
            for item in active_items:
                channel = item.data(CHANNEL)
                if channel not in active_channels:
                    if channel in dialogs:
                        dialogs[channel].accept()
                    item.setText(channel)
                    icw.addItem(acw.takeItem(acw.row(item)))
            for item in inactive_items:
                if item.data(CHANNEL) in active_channels:
                    acw.addItem(icw.takeItem(icw.row(item)))

        traces = {
            channel:[0]*TRACE_SIZE
            for channel in available_channels
        }
        
        dialogs = {}
        def on_double_clicked(item):
            channel = item.data(CHANNEL)
            if channel in dialogs:
                dialogs[channel].activateWindow()
            else:
                item.setFont(bold_font)
                dialog = ChannelWidget(channel,traces[channel],units=units_d[channel])
                dialogs[channel] = dialog
                def on_finished(_):
                    item.setFont(font)
                    dialogs.pop(channel).deleteLater()
                    self.activateWindow()
                dialog.finished.connect(on_finished)
                dialog.show()
        active_channels_widget.itemDoubleClicked.connect(
            on_double_clicked
        )
        @inlineCallbacks
        def get_samples():
            packet = vm.packet()
            acw = active_channels_widget
            active_channels = [
                acw.item(index).data(CHANNEL)
                for index in range(acw.count())
            ]
            for channel in map(str,active_channels):
                packet.get_sample(channel,key=channel)
            try:
                samples = yield packet.send()
            except Exception, e:
                print e
                if run_check.isChecked():
                    get_samples()
                returnValue(None)
            # might have had channel update since packet send
            active_items = [
                acw.item(index)
                for index in range(acw.count())
            ]
            for item in active_items:
                channel = item.data(CHANNEL)
                if channel not in active_channels:
                    continue
                sample = samples[channel]
                trace = traces[channel]
                trace.pop()
                trace.insert(0,sample)
                item.setText('%.3f\t%s'%(sample,channel))
            if run_check.isChecked():
                get_samples()            
            for dialog in dialogs.values():
                dialog.update_plot()
        def on_run_state_changed(state):
            if state:
                get_samples()
        run_check.stateChanged.connect(on_run_state_changed)

        def on_add():
            channel = inactive_channels_widget.currentItem().data(CHANNEL)
            active_channels = [
                active_channels_widget.item(index).data(CHANNEL)
                for index in range(
                    active_channels_widget.count()
                )
            ]
            active_channels.append(channel)
            vm.set_active_channels(map(str,active_channels))
        add_button.clicked.connect(on_add)
        def on_remove():
            channel = active_channels_widget.currentItem().data(CHANNEL)
            active_channels = [
                active_channels_widget.item(index).data(CHANNEL)
                for index in range(
                    active_channels_widget.count()
                )
            ]
            active_channels.remove(channel)
            vm.set_active_channels(map(str,active_channels))
        remove_button.clicked.connect(on_remove)

        def on_sampling_duration(sampling_duration):
            sampling_duration_label.setText(
                'sampling duration: %d ms' % (
                    int(sampling_duration * 1000)
                )
            )
        vm.get_sampling_duration().addCallback(
            on_sampling_duration
        )
        vm.on_sampling_duration_changed.connect(
            lambda context, sampling_duration:
            on_sampling_duration(sampling_duration)
        )
        
        def on_sampling_duration_clicked():
            vm.set_sampling_duration(
                sampling_duration_spin.value()/1000.
            )
        sampling_duration_button.clicked.connect(
            on_sampling_duration_clicked
        )

        def on_triggering(is_triggering):
            triggering_label.setText(
                'trigger enabled'
                if is_triggering else
                'trigger disabled'
            )
        vm.is_triggering().addCallback(on_triggering)
        vm.on_triggering_changed.connect(
            lambda context, is_triggering:
            on_triggering(is_triggering)
        )

        @inlineCallbacks
        def on_triggering_clicked():
            is_triggering = yield vm.is_triggering()
            vm.set_triggering(not is_triggering)
        triggering_button.clicked.connect(on_triggering_clicked)

        vm.on_active_channels_changed.connect(
            lambda context, channels: update_channels(channels)
        )
        
    def closeEvent(self,event):
        event.accept()
        if reactor.running:
            reactor.stop()

class ChannelWidget(QtGui.QDialog):
    def __init__(self,channel,trace,units):
        QtGui.QDialog.__init__(self)
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        plot_widget = PlotWidget(
            title='%s trace' % channel, 
            labels={'left':units}
                    )
        layout.addWidget(plot_widget)
        plot = plot_widget.plot(trace)
        self.plot = plot
        self.trace = trace
    def update_plot(self):
        self.plot.setData(self.trace)
if __name__ == '__main__':
    @inlineCallbacks
    def main():
        cxn = yield connectAsync()
        vm_widget = VoltmeterWidget(cxn.voltmeter)
        container.append(vm_widget)
        vm_widget.show()
    container = []
    reactor.callWhenRunning(main)
    reactor.run()
