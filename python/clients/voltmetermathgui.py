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
from operator import add, sub, mul, div
from voltmeterclient import VoltmeterClient
import numpy as np

MAX_AVERAGE = 10000
MAX_SHOTS = 600
HISTORY = 150

ADD = '+'
SUBTRACT = '-'
MULTIPLY = '*'
DIVIDE = '/'
operations = {
    ADD:add,
    SUBTRACT:sub,
    MULTIPLY:mul,
    DIVIDE:div
}

OPERATION_TYPE = 0
CHANNEL_TYPE = 1
NUMBER_TYPE = 2

class InvalidFormulaException(Exception): pass

def moving_average(a, n) :
    ret = np.cumsum(a, dtype=float)
    ret[n:] = ret[n:] - ret[:-n]
    return ret[n - 1:] / n

class VoltmeterMathMainWidget(QtGui.QWidget):
    def __init__(self,vm_server):
        QtGui.QWidget.__init__(self)
        self.init_gui()

    @inlineCallbacks
    def init_gui(self):
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        
        tab_widget = QtGui.QTabWidget()
        tab_widget.setTabsClosable(True)
        layout.addWidget(tab_widget)

        controls_layout = QtGui.QHBoxLayout()
        
        new_button = QtGui.QPushButton('new')
        controls_layout.addWidget(new_button)

        controls_layout.addStretch()

        client = yield connectAsync()
        vm = client.voltmeter
        available_channels = yield vm.get_available_channels()

        def parse_raw_formula(raw_formula):
            formula = []
            for entry in [
                str(entry.strip()) for entry in raw_formula.split('|')
            ]:
                if entry in operations:
                    formula.append((OPERATION_TYPE,operations[entry]))
                    continue
                if entry in available_channels:
                    formula.append((CHANNEL_TYPE,entry))
                    continue
                try:
                    formula.append((NUMBER_TYPE,float(entry)))
                except ValueError:
                    raise Exception(entry)
            return formula
            
        def on_new():
            raw_formula, success = QtGui.QInputDialog.getText(
                self,
                'enter formula',
                'enter formula in reverse polish notation, separating entries with | symbol'
            )
            if not success: return
            try:
                formula = parse_raw_formula(raw_formula)
                name, success = QtGui.QInputDialog.getText(
                    self,
                    'enter name',
                    'enter plot name'
                )
                if success and name:                    
                    tab_widget.addTab(
                        VoltmeterMathWidget(formula),
                        name
                    )                            
            except InvalidFormulaException, e:
                QtGui.QMessageBox.warning(
                    self,
                    'invalid formula',
                    'formula entry "%s" is neither operation' \
                    'nor channel nor floating point number' % e.message
                )
        new_button.clicked.connect(on_new)
        new_button.click()

class VoltmeterMathWidget(QtGui.QWidget):
    def __init__(self,formula):
        QtGui.QWidget.__init__(self)
        self.formula = formula
        self.init_gui()

    @inlineCallbacks
    def init_gui(self):
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)

        plot_widget = PlotWidget()
        layout.addWidget(plot_widget)
        
        fragments = []
        for type, entry in self.formula:
            if type is CHANNEL_TYPE:
                fragments.append('(%s)'%entry)
            elif type is OPERATION_TYPE:
                fragments.append(
                    {
                        value:key for key, value in operations.items()
                    }[entry]
                )
            elif type is NUMBER_TYPE:
                fragments.append(str(entry))        
        formula_label = QtGui.QLabel('\t'.join(fragments))
        layout.addWidget(formula_label)

        controls_layout = QtGui.QHBoxLayout()
        layout.addLayout(controls_layout)
        
        controls_layout.addWidget(QtGui.QLabel('moving average'))
        moving_average_spin = QtGui.QSpinBox()
        moving_average_spin.setSuffix('samples')
        moving_average_spin.setRange(1,MAX_AVERAGE)
        controls_layout.addWidget(moving_average_spin)

        controls_layout.addStretch()

        controls_layout.addWidget(QtGui.QLabel('shots averaging'))
        shots_spin = QtGui.QSpinBox()
        shots_spin.setSuffix('shots')
        shots_spin.setRange(1,MAX_SHOTS)
        controls_layout.addWidget(shots_spin)

        controls_layout.addStretch()

        run_check = QtGui.QCheckBox('run')
        controls_layout.addWidget(run_check)

        plot = plot_widget.plot()

        client = yield connectAsync()

        vm = client.voltmeter

        self.trace = np.zeros(HISTORY+MAX_AVERAGE)

        def on_moving_average_changed(_):
            update_plot()
        moving_average_spin.valueChanged.connect(on_moving_average_changed)

        def update_plot():
            samples = moving_average_spin.value()
            plot.setData(
                moving_average(self.trace[:HISTORY+samples-1],samples)
            )

        @inlineCallbacks
        def on_run():
            if run_check.isChecked():
                sample = yield get_sample()
                self.trace = np.roll(self.trace,1)
                self.trace[0] = sample
                update_plot()
                on_run()
        run_check.clicked.connect(on_run)        

        @inlineCallbacks
        def get_sample():
            deferreds = {}
            shots = shots_spin.value()
            channels = tuple(set([entry for type, entry in self.formula if type is CHANNEL_TYPE]))
            packet = vm.packet()
            voltages = {channel:0. for channel in channels}
            for channel in channels:
                packet.get_sample(channel)
            for shot in range(shots):
                response = yield packet.send()
                if len(channels) is 1:
                    voltages[channels[0]]+=response.get_sample/shots
                elif len(channels) > 1:
                    for channel, voltage in zip(channels,response.get_sample):
                        voltages[channel]+=voltage/shots                
            stack = []
            for type, entry in self.formula:
                if type is OPERATION_TYPE:
                    v1 = stack.pop()
                    v2 = stack.pop()
                    stack.append(entry(v2,v1))
                else:
                    if type is CHANNEL_TYPE:
                        stack.append(voltages[entry])
                    else:
                        stack.append(entry)
            returnValue(stack.pop())

if __name__ == '__main__':
    def main():
        vm_widget = VoltmeterMathMainWidget(None)
        container.append(vm_widget)
        vm_widget.show()
    container = []
    reactor.callWhenRunning(main)
    reactor.run()
