# TODO:
# update duration on the fly
import sys
from PySide import QtGui, QtCore
if QtCore.QCoreApplication.instance() is None:
    app = QtGui.QApplication(sys.argv)
    import qt4reactor
    qt4reactor.install()
import pyqtgraph as pg
from pyqtgraph import PlotWidget
import pyqtgraph.exporters
from twisted.internet.defer import Deferred, inlineCallbacks, returnValue
from twisted.internet import reactor
from labrad.wrappers import connectAsync
from filecreation import get_filename
from functools import partial
import numpy as np
import os

pg.setConfigOption('background','w')
pg.setConfigOption('foreground','k')

AUGER_OUTPUT_CHANNEL = 'auger output'
AUGER_INPUT_CHANNEL = 'auger input'
PRESET, CREATE = 0,1
REG_DIR = ['','Clients','Auger']
AO_UPDATE_RATE = 40. # response time of hv supply in v/s (conservative)
NAME, START, STOP, STEP, DURATION = 'name', 'start','stop','step','duration'
SETTINGS = (START,STOP,STEP,DURATION)
MIN, MAX, UNITS = 0,1,2
SPIN_SETTINGS = {
    START:{
        MIN:0,
        MAX:999,
        UNITS:'v'
    },
    STOP:{
        MIN:0,
        MAX:999,
        UNITS:'v'
    },
    STEP:{
        MIN:1,
        MAX:9999,
        UNITS:'mv'
    },
    DURATION:{
        MIN:1,
        MAX:9999,
        UNITS:'ms'
    }
}

class AugerWidget(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.init_widget()

    @inlineCallbacks
    def init_widget(self):
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        
        class TraceWidget(PlotWidget):
            settings_updated = QtCore.Signal()
            def __init__(self,settings):
                PlotWidget.__init__(self)
                self.trace = self.plot(
                    [],
                    [],
                    pen=None,
                    symbol='o',
                    symbolPen=None,
                    symbolSize=3
                )
                self.update_settings(settings)

            def update_settings(self,settings):
                self.settings = settings
                self.setTitle(settings[NAME])
                self.setLabels(
                    bottom='auger energy (eV)',
                    left='auger signal (V)'
                )
                self.index = 0
                start, stop, step = (
                    settings[START],
                    settings[STOP],
                    settings[STEP]
                )
                step = step/1000.
                self.energies = (
                    np.arange(start,stop,step)
                    if stop > start else
                    np.arange(stop,start,step)[::-1]
                )
                self.trace_data = {}
                self.settings_updated.emit()
                
            def edit_settings(self):
                trace_dialog = TraceDialog(self,self.settings)
                def on_finished(result):
                    if result == trace_dialog.Accepted:
                        self.update_settings(
                            trace_dialog.get_settings()
                        )
                    trace_dialog.close()
                trace_dialog.finished.connect(on_finished)
                trace_dialog.show()

            def get_settings(self):
                return self.settings

            def update_trace(self,energy,signal):
                self.trace_data[energy] = signal
                self.trace.setData(
                    *zip(*self.trace_data.items())
                )

            def get_next_energy(self):
                index = self.index
                self.index += 1
                done = self.index is len(self.energies)
                if done:
                    self.index = 0
                return done, self.energies[index]

            def reset(self):
                self.index = 0

            def save_image(self,filename):
                pg.exporters.ImageExporter(
                    self.plotItem
                ).export(filename)

            def save_data(self,filename):
                np.savetxt(
                    filename,
                    self.trace_data.items()
                )

        class TraceTabWidget(QtGui.QTabWidget):
            trace_added = QtCore.Signal(TraceWidget)
            on_trace_remove_requested = QtCore.Signal(TraceWidget)
            def __init__(self):
                QtGui.QTabWidget.__init__(self)
                self.setTabsClosable(True)
                def on_tab_remove_requested(index):
                    self.on_trace_remove_requested.emit(
                        self.widget(index)
                    )                    
                self.tabCloseRequested.connect(
                    on_tab_remove_requested
                )
            def add_trace(self,trace_widget,name):
                self.addTab(trace_widget,name)
                def on_settings_updated():
                    self.setTabText(
                        self.indexOf(trace_widget),
                        trace_widget.get_settings()[NAME]
                    )
                trace_widget.settings_updated.connect(
                    on_settings_updated
                )
                self.trace_added.emit(trace_widget)

            def current_trace(self):
                current_index = self.currentIndex()
                if current_index == -1:
                    return None
                else:
                    return self.widget(current_index)

            def remove_trace(self,trace):
                self.removeTab(self.indexOf(trace))
                trace.deleteLater()
                
        trace_tab_widget = TraceTabWidget()
        layout.addWidget(trace_tab_widget)

        add_layout = QtGui.QHBoxLayout()
        layout.addLayout(add_layout)

        add_button = QtGui.QPushButton('add')
        add_layout.addWidget(add_button)

        presets_combo = QtGui.QComboBox()
        add_layout.addWidget(presets_combo)
        presets_combo.setSizeAdjustPolicy(
            presets_combo.AdjustToContents
        )                

        add_layout.addStretch()

        save_preset_button = QtGui.QPushButton('save preset')
        add_layout.addWidget(save_preset_button)

        scan_layout = QtGui.QHBoxLayout()
        layout.addLayout(scan_layout)

        scan_button = QtGui.QPushButton('scan')
        scan_layout.addWidget(scan_button)

        stop_button = QtGui.QPushButton('stop')
        scan_layout.addWidget(stop_button)

        edit_button = QtGui.QPushButton('edit')
        scan_layout.addWidget(edit_button)

        repeat_check = QtGui.QCheckBox('repeat')
        scan_layout.addWidget(repeat_check)

        scan_layout.addStretch()

        save_trace_button = QtGui.QPushButton('save trace')
        scan_layout.addWidget(save_trace_button)

        status_label = QtGui.QLabel()
        layout.addWidget(status_label)
        status_label.setText('stopped')

        client = yield connectAsync()
        vm = client.voltmeter
        yield vm.set_active_channels(
            [AUGER_INPUT_CHANNEL]
        )
        ao = client.analog_output
        
        reg = client.registry        
        yield reg.cd(REG_DIR)
        reg.notify_on_change(111,True)
        reg.addListener(
            listener=lambda context, message: setup_presets(),
            source=None,
            ID=111
        )
        @inlineCallbacks
        def setup_presets():
            presets_combo.clear()
            presets_combo.addItem('create new',userData=CREATE)
            yield reg.cd(REG_DIR)
            preset_names, _ = yield reg.dir()
            for preset_name in preset_names:
                presets_combo.addItem(
                    preset_name,
                    userData=PRESET
                )
        yield setup_presets()
        class TraceDialog(QtGui.QDialog):
            def __init__(self,parent,default_settings=None):
                QtGui.QDialog.__init__(self,parent)
                layout = QtGui.QVBoxLayout()
                self.setLayout(layout)
                form_layout = QtGui.QFormLayout()
                layout.addLayout(form_layout)
                name_edit = self.name_edit = QtGui.QLineEdit()
                form_layout.addRow(NAME,name_edit)
                spins = self.spins = {}                
                for setting_name, settings in SPIN_SETTINGS.items():
                    spin = QtGui.QSpinBox()
                    spin.setMinimum(settings[MIN])
                    spin.setMaximum(settings[MAX])
                    spin.setSuffix(settings[UNITS])
                    form_layout.addRow(setting_name,spin)
                    spins[setting_name] = spin
                if default_settings is not None:
                    for setting_name in SETTINGS:
                        spins[setting_name].setValue(
                            default_settings[setting_name]
                        )
                    self.name_edit.setText(
                        default_settings[NAME]
                    )
                buttons_layout = QtGui.QHBoxLayout()
                layout.addLayout(buttons_layout)
                ok_button = QtGui.QPushButton('ok')
                ok_button.clicked.connect(self.accept)
                buttons_layout.addWidget(ok_button)
                cancel_button = QtGui.QPushButton('cancel')
                buttons_layout.addWidget(cancel_button)
                cancel_button.clicked.connect(self.reject)
                buttons_layout.addStretch()

            def get_settings(self):
                name = self.name_edit.text()
                name = name if name else 'untitled'
                settings = {
                    NAME:name
                }
                settings.update(
                    {
                        setting:spin.value()
                        for setting, spin in
                        self.spins.items()
                    }
                )
                return settings
            
        @inlineCallbacks
        def on_add():
            current_index = presets_combo.currentIndex()
            preset_type = presets_combo.itemData(current_index)
            if preset_type is PRESET:
                name = presets_combo.itemText(current_index)
                yield reg.cd(REG_DIR)
                yield reg.cd(name)
                settings = {}
                settings[NAME] = name
                _, setting_names = yield reg.dir()
                for setting_name in SETTINGS:
                    if setting_name not in setting_names:
                        QtGui.QMessageBox.information(
                            self,
                            'preset not properly configured',
                            'preset is missing %s entry' % setting_name
                        )
                        returnValue(None)
                    setting = yield reg.get(setting_name)
                    settings[setting_name] = setting
                trace_tab_widget.add_trace(
                    TraceWidget(settings),
                    name
                )
            elif preset_type is CREATE:
                trace_dialog = TraceDialog(self)
                def on_finished(result):
                    settings = trace_dialog.get_settings()
                    if result == trace_dialog.Accepted:
                        trace_tab_widget.add_trace(
                            TraceWidget(settings),
                            settings[NAME]
                        )
                    trace_dialog.close()
                trace_dialog.finished.connect(on_finished)
                trace_dialog.show()
        add_button.clicked.connect(on_add)
        def on_scan():
            @inlineCallbacks
            def start_scan():
                @inlineCallbacks
                def loop(done,energy):
                    continue_token = continue_control[0]
                    signal = yield vm.get_sample(
                        AUGER_INPUT_CHANNEL
                    )
                    if continue_token:
                        trace.update_trace(energy,signal)
                        if done:
                            if repeat_check.isChecked():
                                start_scan()
                            else:
                                status_label.setText('stopped')
                        else:
                            done, energy = trace.get_next_energy()
                            yield ao.set_value(
                                AUGER_OUTPUT_CHANNEL,
                                energy
                            )
                            loop(done, energy)
                trace = trace_to_scan
                trace.reset()
                duration = trace.get_settings()[DURATION]
                yield vm.set_sampling_duration(duration/1000.)
                done, initial_energy = trace.get_next_energy()
                previous_energy = yield ao.get_value(AUGER_OUTPUT_CHANNEL)
                delta_energy = abs(initial_energy-previous_energy)
                yield ao.set_value(AUGER_OUTPUT_CHANNEL,initial_energy)
                QtCore.QTimer.singleShot(
                    int(1000*delta_energy / AO_UPDATE_RATE),
                    partial(loop,done,initial_energy)
                )
            trace_to_scan = trace_tab_widget.current_trace()
            if trace_to_scan is None: return
            if self.scanning:
                continue_control.pop().pop() # signal to current execution to discard last point and stop scanning
                continue_control.append([None])
            self.scanning_trace = trace_to_scan
            self.scanning = True
            status_label.setText('scanning %s' % trace_to_scan.get_settings()[NAME])
            start_scan()
        continue_control = [[None]]
        scan_button.clicked.connect(on_scan)
        def on_stop():
            continue_control.pop().pop()
            continue_control.append([[None]])
            status_label.setText('stopped')
            self.scanning = False
            self.scanning_trace = None
        stop_button.clicked.connect(on_stop)
        self.scanning = False
        self.scanning_trace = None
        def on_trace_remove_requested(trace):
            if trace is self.scanning_trace:
                on_stop()
            trace_tab_widget.remove_trace(trace)
        trace_tab_widget.on_trace_remove_requested.connect(
            on_trace_remove_requested
        )
        def on_edit():
            current_trace = trace_tab_widget.current_trace()
            if current_trace is not None:
                current_trace.edit_settings()
        edit_button.clicked.connect(on_edit)
        @inlineCallbacks
        def on_save_preset():
            current_trace = trace_tab_widget.current_trace()
            if current_trace is None:
                returnValue(None)
            settings = current_trace.get_settings()            
            yield reg.cd(REG_DIR)
            presets, _ = yield reg.dir()
            name = settings[NAME]
            if name in presets:
                button = QtGui.QMessageBox.question(
                    self,
                    'preset name already exists',
                    'preset name "%s"already exists. overwrite?' % name,
                    QtGui.QMessageBox.Save,
                    QtGui.QMessageBox.Cancel
                )
                if button != QtGui.QMessageBox.Save:
                    returnValue(None)
            else:
                yield reg.mkdir(name)
            for setting_name in SETTINGS:
                yield reg.cd(REG_DIR+[name])
                yield reg.set(
                    setting_name,
                    settings[setting_name]
                )
        save_preset_button.clicked.connect(on_save_preset)
        def on_save_trace():
            current_trace = trace_tab_widget.current_trace()
            if current_trace is None:
                return
            description, success = QtGui.QInputDialog.getText(
                self,
                'enter description',
                'enter optional description'
            )
            description = '_'.join(
                [
                    current_trace.get_settings()[NAME]
                ] + (
                    [description]
                    if success and description else
                    []
                )
            )
            filename = get_filename(
                description=description,
                extension='dat'
            )
            current_trace.save_data(filename)
            current_trace.save_image(
                '.'.join(
                    (
                        os.path.splitext(filename)[0],
                        'png'
                    )
                )
            )
        save_trace_button.clicked.connect(on_save_trace)
        presets_combo.setCurrentIndex(
            presets_combo.findData(PRESET)
        )
        on_add()
    def closeEvent(self,event):
        if reactor.running:
            reactor.stop()
        event.accept()

if __name__ == '__main__':
    def main():
        auger_widget = AugerWidget()
        container.append(auger_widget)
        auger_widget.show()
    container = []
    reactor.callWhenRunning(main)
    reactor.run()
