import sys
from PySide import QtGui, QtCore
if QtCore.QCoreApplication.instance() is None:
    app = QtGui.QApplication(sys.argv)
    import qt4reactor
    qt4reactor.install()
from twisted.internet.defer import Deferred, inlineCallbacks, returnValue
from twisted.internet import reactor
import numpy as np
from scipy.optimize import curve_fit
from jsonwidget import JsonWidget
from jsonmodel import JsonModel
from pyqtgraph import GraphicsWindow, PlotItem, PlotDataItem
from labrad.wrappers import connectAsync
from labrad.types import Error

from scandefs import *
from scanitems import TestScanInput, TestOutput, StepperMotorInput, VoltmeterOutput, DelayGeneratorInput, VoltmeterMathOutput
from util import mangle
from filecreation import get_datetime

# scan inputs and associated keys
INPUTS = {
    TEST:TestScanInput,
    STEPPER_MOTOR:StepperMotorInput,
    DELAY_GENERATOR:DelayGeneratorInput
}

# scan outputs and associated keys
OUTPUTS = {
    TEST:TestOutput,
    VOLTMETER:VoltmeterOutput,
    VOLTMETER_MATH:VoltmeterMathOutput
}

# number of points in optimized fit curve
FIT_POINTS = 100

# directory in datavault to store scan data
data_vault_dir = ['scans']

# one of these are instantiated for every scan in scan list
class ScanPlot(PlotItem):
    # scan is the scan json object
    def __init__(self,parent,scan):
        # name of independent variable
        input = scan[INPUT]
        x_label = input.get(NAME,'input')
        x_units = input.get(UNITS,'arb')
        # name of dependent variable
        output = scan[OUTPUT]
        if type(output) is dict:
            y_label = output.get(NAME,'output')
            y_units = output.get(UNITS,'arb')            
        else:
            y_label = 'output'
            y_units = 'arb'
        # scan title
        title = scan.get(
            NAME,
            '%s vs. %s' % (y_label,x_label)
        )
        labels = {
            'bottom':'%s (%s)' % (x_label,x_units),
            'left':'%s (%s)' % (y_label,y_units)
        }
        # initialize pyqtgraph plot item with title and axis labels
        PlotItem.__init__(
            self,
            title = title,
            labels = labels
        )
        # are we setting input to optimal value of scan result?
        self.optimizing = scan.get(OPTIMIZE,False)
        # if we have multiple outputs and are optimizing, which output to optimize?
        self.optimize_axis = scan.get(OPTIMIZE_AXIS,0)
        # are we saving scan data to datavault?
        self.saving = scan.get(SAVE,False)
        # are we returning to input's original position after scan?
        self.returning = scan.get(RETURN,False)
        self.scan = scan
        self.__parent = parent

    # performs set up for scan
    def start(self):
        return self.set_scan_items()
    
    @inlineCallbacks
    def set_scan_items(self):
        scan = self.scan
        outputs = scan[OUTPUT]
        if type(outputs) is dict:
            outputs = [outputs]
        if self.is_saving():
            # get labrad connection
            cxn = yield connectAsync()
            # get handle to data vault
            data_vault = cxn.data_vault
            # list of folders (trunk to leaf) for dataset directory
            save_dir = scan.get(SAVE_DIR,[])
            # go to scans dir in dv
            yield data_vault.cd(data_vault_dir+save_dir,True)
            independent_variables = [
                '%s [%s]' % (
                    scan[INPUT].get(NAME,'input'),
                    scan[INPUT].get(UNITS,'arb')
                )
            ]
            dependent_variables = [
                '%s [%s]' % (
                    output.get(NAME,'output'),
                    output.get(UNITS,'arb')
                ) for output in outputs
            ]
            save_name = scan.get(SAVE_NAME,None)
            default_name = text=scan.get(NAME,'')
            if save_name is None:
                save_name, result = QtGui.QInputDialog.getText(
                    self.__parent,
                    'enter dataset name',
                    'enter title for data vault dataset',
                    text = default_name
                )
                if not result:
                    save_name = default_name
            # create new dataset                
            yield data_vault.new(
                str(save_name),
                independent_variables,
                dependent_variables
            )
            # make note of dataset creation
            yield data_vault.add_parameter(
                'time',
                get_datetime()
            )
            self.data_vault = data_vault
        # instantiate scan input object
        self.input = INPUTS[
            scan[INPUT][CLASS]
        ](
            **mangle(scan[INPUT].get(ARGS,{}))
        )
        # note initial position if we are planning to return to it after scan
        if self.is_returning():
            self._return_input = yield self.input._get_input()
        # instantiate scan output object
        self.outputs = [
            OUTPUTS[
                output[CLASS]
            ](
                **mangle(output.get(ARGS,{}))
            ) for output in outputs
        ]
        # intialize x and y values
        self.x_data = []
        self.y_datas = []
        # clear any stuff that happens to be in plot (TODO: do we ever scan the same object twice?)
        for item in self.allChildItems():
            self.removeItem(item)            
        # if optimizing or have multiple sources, \
        # add legend to distinguish different sources
        if self.is_optimizing() or len(outputs) > 1:
            self.addLegend()
        if self.is_optimizing():
            # initialize fit curve
            self.fit_curve = PlotDataItem(
                name='fit (%s)' % outputs[
                    self.optimize_axis
                ].get(
                    NAME,
                    'output %d' % (self.optimize_axis+1)
                ),
                pen={'color':'BBB','width':2}
            )
        # initialize data curves
        self.curves = [
            self.plot(
                name=output.get(NAME,'output %d' % (index + 1)),
                pen=None,
                symbolSize=5,
                symbolPen=None,
                symbolBrush=('F55','5F5','55F','FF5','5FF','F5F')[index % 6]
            ) for index, output in enumerate(outputs)
        ]

    def show_fit(self):
        self.addItem(self.fit_curve)

    # put input back to initial position
    def return_input(self):
        return self.input.set_input(self._return_input)

    # called to increment scan by one step
    @inlineCallbacks
    def step(self):
        # ask input for next x value
        x = yield self.input.get_input()
        # check if scan input is done and err if so
        if x is None:
            returnValue(False)
        y = []
        output_deferreds = [
            output.get_output() for output in self.outputs
        ]
        for deferred in output_deferreds:
            y_value = yield deferred
            y.append(y_value)
        # add new values to data arrays
        self.x_data.append(x)
        self.y_datas.append(y)        
        # update dataset with new datapoint if saving
        if self.is_saving():
            yield self.data_vault.add([x]+y)
        for curve, y_data in zip(self.curves,zip(*self.y_datas)):
            # update data curve
            curve.setData(self.x_data,y_data)
        # indicate successful step
        returnValue(True)

    def is_optimizing(self):
        return self.optimizing

    def is_saving(self):
        return self.saving

    def is_returning(self):
        return self.returning    

    # fit data to gaussian to find input value that optimizes output and set input to that value
    @inlineCallbacks
    def optimize_input(self):        
        x_arr = np.array(self.x_data)
        y_arr = np.array(zip(*self.y_datas)[self.optimize_axis])
        params = self.estimate_gaussian_parameters(
            x_arr,y_arr
        )
        try:
            params, _ = curve_fit(
                self.gaussian,
                x_arr,
                y_arr,
                params
            )
        except RuntimeError:
            pass
        x_fit = np.linspace(x_arr.min(),x_arr.max(),FIT_POINTS)            
        self.fit_curve.setData(
            x_fit,
            self.gaussian(x_fit,*params)
        )
        if self.fit_curve not in self.listDataItems():
            self.show_fit()
            yield self.input.set_input(
                int(
                    np.round(
                        params[0]
                    )
                )
            )

    @staticmethod
    def gaussian(x,mean,std,amplitude,offset):
        return amplitude * np.exp(- 1. / 2. * np.square( ( x - mean ) / std) ) + offset

    @staticmethod
    def estimate_gaussian_parameters(x,y):
        min = y.min()
        max = y.max()
        offset = min
        amplitude = max - min
        mean_index = y.argmax()
        mean = x[mean_index]
        threshold = min + (max - min) / 2
        right_estimate = None
        index = mean_index
        while True:
            if index == len(y):
                break
            if y[index] < threshold:
                right_estimate = abs(x[index] - mean) / 2.355 * 2
            index += 1
        left_estimate = None
        index = mean_index
        while True:
            if index < 0:
                break
            if y[index] < threshold:
                left_estimate = abs(x[index] - mean) / 2.355 * 2
            index -= 1
        if right_estimate is None and left_estimate is None:
            std = abs(x[len(y)/2]-x[0])
        elif right_estimate is None:
            std = left_estimate
        elif left_estimate is None:
            std = right_estimate
        else:
            std = ( left_estimate + right_estimate ) / 2.
        return (mean,std,amplitude,offset)

class ScanExecWidget(QtGui.QWidget):
    def __init__(self,model):
        QtGui.QWidget.__init__(self)
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        
        plot_group = GraphicsWindow()
        layout.addWidget(plot_group)

        controls_layout = QtGui.QHBoxLayout()
        layout.addLayout(controls_layout)        

        # starts / stops execution of scan
        run_check = QtGui.QCheckBox('run')
        controls_layout.addWidget(run_check)
        # boolean that tracks running state of scan
        self.running = False
        # list of scan plot objects
        self.scan_plots = []
        # run current scan list
        def start():
            # set execution status to running
            self.running = True
            # scan index identifies scan object current executing
            self.scan_index = 0
            # lets loop() functio know that current scan object requires initialization
            self.init_scan = True
            # extract scan json object from scan tree
            scans = model.to_json()
            # destroy previously existing scan objects
            for scan_plot in self.scan_plots:
                plot_group.removeItem(scan_plot)
            # create new scan objects from scan json object
            self.scan_plots = [
                ScanPlot(self,scan) for scan in scans
            ]
            # add new scan objects to plot group
            for scan_plot in self.scan_plots:
                plot_group.addItem(scan_plot)
            # start scanning
            loop()
        @inlineCallbacks
        def loop():
            def end_scan():
                self.running = False
                run_check.setChecked(False)
                status_label.setText('stopped')
            @inlineCallbacks
            def end_scan_object(confirm=False):
                optimizing = False
                returning = False
                # if optimize is requested, make sure we still want it
                if scan_plot.is_optimizing():
                    if confirm:
                        button = QtGui.QMessageBox.question(
                            self,
                            'optimize scan?',
                            'scan is set to optimize. proceed with optimization?',
                            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No
                        )
                        if button & QtGui.QMessageBox.Yes:
                            optimizing = True
                    else:
                        optimizing = True
                    if optimizing:
                        status_label.setText('optimizing')
                        try:
                            yield scan_plot.optimize_input()
                        except Exception, e:
                            QtGui.QMessageBox.warning(
                                self,
                                'error on optimize',
                                e.msg if hasattr(e,'msg') else str(e)
                            )
                        status_label.setText('running')
                # if return is requested, make sure we still want it
                if scan_plot.is_returning() and not optimizing:
                    if confirm:
                        button = QtGui.QMessageBox.question(
                            self,
                            'return input?',
                            'scan input is set to return to initial position. proceed with return?',
                            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No
                        )
                        if button & QtGui.QMessageBox.Yes:
                            returning = True
                    else:
                        returning = True
                    if returning:
                        status_label.setText('returning')
                        try:
                            yield scan_plot.return_input()
                        except Exception, e:
                            QtGui.QMessageBox.warning(
                                self,
                                'error on return',
                                e.msg if hasattr(e,'msg') else str(e)
                            )
                        status_label.setText('running')
            # check if scan list finished
            if self.scan_index is len(self.scan_plots):
                # set state to stopped
                end_scan()
                # break from loop
                returnValue(None)
            # get handle to current scan object
            scan_plot = self.scan_plots[self.scan_index]
            if self.restart_requested or self.skip_requested or self.stop_requested:
                # only clean up if scan already started
                if not self.init_scan:
                    # finish scan object
                    yield end_scan_object(confirm=True)
                if self.stop_requested:
                    # set state to stopped
                    end_scan()
                    # break from loop
                    returnValue(None)
                if self.skip_requested:
                    # move on to next scan object
                    self.scan_index += 1
                # indicate that on next loop scan object needs initialization
                self.init_scan = True
                # untoggle restart, skip, and stop booleans
                self.restart_requested = False
                self.skip_requested = False
                self.stop_requested = False
                loop()
                returnValue(None)
            # run check is cleared so go into pause mode
            if not run_check.isChecked():
                status_label.setText('paused')
                returnValue(None)            
            if self.init_scan:
                self.init_scan = False
                # initialize scan object
                try:
                    result = yield scan_plot.start()
                except Exception, e:
                    QtGui.QMessageBox.warning(
                        self,
                        'error on scan initialization',
                        e.msg if hasattr(e,'msg') else str(e)
                    )
                    end_scan()
                    returnValue(None)
            # execute next scan step
            try:
                result = yield scan_plot.step()
            except Exception, e:
                QtGui.QMessageBox.warning(
                    self,
                    'error on step',
                    e.msg if hasattr(e,'msg') else str(e)
                )
                self.stop_requested = True
                loop()
                returnValue(None)
            # check is scan object completed
            if not result:
                # move on to next scan object
                yield end_scan_object()
                self.init_scan = True
                self.scan_index += 1
            # keep going
            loop()
                
        def on_toggled(state):
            # if untoggling, do nothing. current step will finish and scan will enter pause mode
            if not state:
                return            
            # reset execution control booleans
            self.stop_requested = False
            self.restart_requested = False
            self.skip_requested = False
            status_label.setText('running')
            # was paused, so don't need to initialize, just continue loop
            if self.running:
                loop()
                return
            # start new scan list
            start()      
        run_check.toggled.connect(on_toggled)        

        stop_button = QtGui.QPushButton('stop')
        controls_layout.addWidget(stop_button)
        def on_stop():
            self.stop_requested = True
        stop_button.clicked.connect(on_stop)

        restart_button = QtGui.QPushButton('restart')
        controls_layout.addWidget(restart_button)
        def on_restart():
            self.restart_requested = True
        restart_button.clicked.connect(on_restart)

        skip_button = QtGui.QPushButton('skip')
        controls_layout.addWidget(skip_button)
        def on_skip():
            self.skip_requested = True
        skip_button.clicked.connect(on_skip)

        save_button = QtGui.QPushButton('save')
        controls_layout.addWidget(save_button)
        def on_save():
            pass
        save_button.clicked.connect(on_save)

        controls_layout.addStretch()

        status_label = QtGui.QLabel('stopped')
        controls_layout.addWidget(status_label)

class ScanWidget(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)        

        json_model = JsonModel()        
        scan_exec_widget = ScanExecWidget(json_model)
        self.setCentralWidget(scan_exec_widget)

        scan_tree = JsonWidget(json_model)
        dock_widget = QtGui.QDockWidget('scan tree')
        dock_widget.setWidget(scan_tree)
        self.addDockWidget(
            QtCore.Qt.BottomDockWidgetArea,
            dock_widget
        )
        dock_widget.setFeatures(
            dock_widget.DockWidgetMovable
            |
            dock_widget.DockWidgetFloatable
        )
        scan_tree.load_scan()

    def closeEvent(self,event):
        event.accept()
        reactor.stop()

if __name__ == '__main__':
    def main():
        import json
        import sys
        scan_widget = ScanWidget()
        container.append(scan_widget)
        scan_widget.show()
    container = []
    reactor.callWhenRunning(main)
    reactor.run()
