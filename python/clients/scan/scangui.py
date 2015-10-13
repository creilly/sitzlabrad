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

from scandefs import *
from scanitems import TestInput,TestScanInput,TestOutput

INPUTS = {
    TEST:TestInput,
    TEST_SCAN:TestScanInput
}
OUTPUTS = {
    TEST:TestOutput
}

FIT_POINTS = 100

class ScanPlot(PlotItem):
    def __init__(self,scan):
        x_label = scan[INPUT].get(NAME,'input')
        y_label = scan[OUTPUT].get(NAME,'output')
        title = scan.get(
            NAME,
            '%s vs. %s' % (y_label,x_label)
        )
        x_units = scan[INPUT].get(UNITS,'arb units')
        y_units = scan[OUTPUT].get(UNITS,'arb units')
        PlotItem.__init__(
            self,
            title = title,
            labels = {
                'bottom':'%s (%s)' % (x_label,x_units),
                'left':'%s (%s)' % (y_label,y_units),
            }
        )        
        self.optimize = scan[OPTIMIZE]
        self.scan = scan

    def start(self):
        self.set_scan_items()

    def restart(self):
        return self.start()

    def set_scan_items(self):
        scan = self.scan
        self.input = INPUTS[
            scan[INPUT][CLASS]
        ](
            **scan[INPUT][ARGS]
        )
        self.output = OUTPUTS[
            scan[OUTPUT][CLASS]
        ](
            **scan[OUTPUT][ARGS]
        )
        self.x_arr = []
        self.y_arr = []
        for item in self.allChildItems():
            self.removeItem(item)
        if self.is_optimizing():
            self.addLegend()
            self.fit_curve = PlotDataItem(
                name='fit', pen={'color':'4FF','width':2}
            )
        self.curve = PlotDataItem(
            name='data', pen=None, symbolSize=5, symbolPen=None, symbolBrush='F4F'
        )
        self.addItem(self.curve)        

    def show_fit(self):
        self.addItem(self.fit_curve)

    @inlineCallbacks
    def step(self):
        x = yield self.input.get_input()        
        if x is None:
            returnValue(False)
        self.x_arr.append(x)
        y = yield self.output.get_output()
        self.y_arr.append(y)
        self.curve.setData(self.x_arr,self.y_arr)
        returnValue(True)        

    def is_optimizing(self):
        return self.optimize

    @inlineCallbacks
    def optimize_input(self):
        x_arr = np.array(self.x_arr)
        y_arr = np.array(self.y_arr)
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
        
        run_check = QtGui.QCheckBox('run')
        controls_layout.addWidget(run_check)
        self.running = False        
        self.scan_plots = []
        def start():
            self.running = True
            self.scan_index = 0
            self.scan_iter = None
            self.stop_requested = False
            self.restart_requested = False
            self.skip_requested = False
            self.init_scan = True
            scans = model.to_json()
            for scan_plot in self.scan_plots:
                plot_group.removeItem(scan_plot)
            self.scan_plots = [
                ScanPlot(scan) for scan in scans
            ]
            for scan_plot in self.scan_plots:
                plot_group.addItem(scan_plot)
            loop()
        @inlineCallbacks
        def loop():
            if (
                self.stop_requested 
                or 
                self.scan_index is len(self.scan_plots)
            ):
                self.running = False
                self.stop_requested = False
                run_check.setChecked(False)
                returnValue(None)
            if self.restart_requested:
                self.init_scan = True
                self.restart_requested = False
                loop()                
                returnValue(None)
            if not run_check.isChecked():
                returnValue(None)
            scan_plot = self.scan_plots[self.scan_index]
            if self.skip_requested:
                if scan_plot.is_optimizing():
                    button = QtGui.QMessageBox.question(
                        self,
                        'optimize scan?',
                        'scan is set to optimize. proceed with optimization?',
                        QtGui.QMessageBox.Yes | QtGui.QMessageBox.No
                    )
                    if button & QtGui.QMessageBox.Yes:
                        yield scan_plot.optimize_input()
                    self.init_scan = True
                    self.scan_index += 1
                    self.skip_requested = False
                    loop()
                    returnValue(None)
            if self.init_scan:
                self.scan_iter = scan_plot.start()
                self.init_scan = False
            result = yield scan_plot.step()
            if not result:
                if scan_plot.is_optimizing():
                    yield scan_plot.optimize_input()
                self.init_scan = True
                self.scan_index += 1
            loop()
                
        def on_toggled(state):
            if not state:
                return
            if self.running:
                loop()
                return
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

class ScanWidget(QtGui.QMainWindow):
    def __init__(self,scans):
        QtGui.QMainWindow.__init__(self)        

        json_model = JsonModel()        
        for scan in scans:
            json_model.append_scan(scan)
        scan_exec_widget = ScanExecWidget(json_model)
        self.setCentralWidget(scan_exec_widget)

        scan_tree = JsonWidget(json_model)
        dock_widget = QtGui.QDockWidget('scan tree')
        dock_widget.setWidget(scan_tree)
        self.addDockWidget(
            QtCore.Qt.BottomDockWidgetArea,
            dock_widget
        )

    def closeEvent(self,event):
        event.accept()
        reactor.stop()

if __name__ == '__main__':
    def main():
        import json
        with open('scans/test.json','r') as f:
            scans = json.loads(f.read())
        scan_widget = ScanWidget(scans)
        container.append(scan_widget)
        scan_widget.show()
    container = []
    reactor.callWhenRunning(main)
    reactor.run()
