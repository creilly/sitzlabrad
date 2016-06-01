import sys
from PySide import QtGui, QtCore
if QtCore.QCoreApplication.instance() is None:
    app = QtGui.QApplication(sys.argv)
    import qt4reactor
    qt4reactor.install()
import pyqtgraph as pg
from pyqtgraph import PlotWidget
from twisted.internet.defer import Deferred, inlineCallbacks, returnValue
from twisted.internet import reactor
from labrad.wrappers import connectAsync
from filecreation import get_filename
from functools import partial
import numpy as np
import os
from time import clock

pg.setConfigOption('background','w')
pg.setConfigOption('foreground','k')

HISTORY = 200
DELTA_CONTROL = 0.0015
FILAMENT_CHANNEL = 'filament control output'
TIME = 'time'
INPUTS = (TIME,)
FILAMENT_CONTROL, EMISSION_CURRENT, TEMPERATURE, TEMPERATURE_SETPOINT, RATE, RATE_SETPOINT = 'filament control', 'emission current', 'temperature', 'temperature setpoint', 'rate', 'rate setpoint'
OUTPUTS = (FILAMENT_CONTROL,EMISSION_CURRENT,TEMPERATURE,TEMPERATURE_SETPOINT,RATE,RATE_SETPOINT)
EMISSION_CHANNEL = 'emission current'
TEMPERATURE_CHANNEL = 'sample temperature'
VOLTMETER_CHANNELS = (TEMPERATURE_CHANNEL,EMISSION_CHANNEL)
MIN_TEMPERATURE = 100
MAX_TEMPERATURE = 500
TEMPERATURE_BUFFER = 100.
MAX_RAMP_RATE = 1.0
SAMPLING_DURATION = .1
FILAMENT_PW, EMISSION_PW, TEMPERATURE_PW, RATE_PW = 0,1,2,3
PLOTS = (FILAMENT_PW,EMISSION_PW,TEMPERATURE_PW,RATE_PW)
TITLE, TRACES = 0,1
FILAMENT_TRACE,EMISSION_TRACE,TEMPERATURE_TRACE,TEMPERATURE_SETPOINT_TRACE,RATE_TRACE,RATE_SETPOINT_TRACE = 0,1,2,3,4,5
PLOTS_DICT = {
    FILAMENT_PW:{
        TITLE:'filament control',
        TRACES:{FILAMENT_TRACE:'filament control'}
    },
    EMISSION_PW:{
        TITLE:'emission current',
        TRACES:{EMISSION_TRACE:'emission current'}
    },
    TEMPERATURE_PW:{
        TITLE:'sample temperature',
        TRACES:{
            TEMPERATURE_TRACE:'temperature',
            TEMPERATURE_SETPOINT_TRACE:'setpoint'
        }
    },
    RATE_PW:{
        TITLE:'temperature ramp rate',
        TRACES:{
            RATE_TRACE:'ramp rate',
            RATE_SETPOINT_TRACE:'ramp rate setpoint'
        }
    }
}

class HeaterWidget(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.init_widget()

    @inlineCallbacks
    def init_widget(self):
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)

        plot_layout = QtGui.QHBoxLayout()
        layout.addLayout(plot_layout)

        plots = {}        
        traces = {}
        for plot in PLOTS:
            plot_dict = PLOTS_DICT[plot]
            plot_widget = PlotWidget(title=plot_dict[TITLE])
            plot_traces = plot_dict[TRACES]            
            if len(plot_traces) > 1:
                plot_widget.addLegend()
            trace_index = 0
            for trace_key, trace_name in plot_traces.items():
                trace = [0] * HISTORY
                plot = plot_widget.plot(
                    trace,
                    name=trace_name,
                    pen=None,
                    symbol='o',
                    symbolPen=None,
                    symbolSize=3,
                    symbolBrush=('33F','F33')[trace_index % 2]
                )
                plots[trace_key] = plot
                traces[trace_key] = trace
                trace_index += 1
            plot_layout.addWidget(plot_widget)

        controls_layout = QtGui.QHBoxLayout()
        layout.addLayout(controls_layout)
        
        temperature_setpoint_spin = QtGui.QSpinBox()
        temperature_setpoint_spin.setRange(MIN_TEMPERATURE,MAX_TEMPERATURE)
        temperature_setpoint_spin.setPrefix('temp')
        temperature_setpoint_spin.setSuffix('C')
        controls_layout.addWidget(temperature_setpoint_spin)

        controls_layout.addStretch()

        run_check = QtGui.QCheckBox('run')
        controls_layout.addWidget(run_check)
        
        client = yield connectAsync()
        voltmeter = client.voltmeter
        analog_output = client.analog_output        
        data_vault = client.data_vault
        yield data_vault.cd('heater',True)
        yield data_vault.new('heater trial',INPUTS,OUTPUTS)
        
        self.stop_requested = False
        @inlineCallbacks
        def init_voltmeter():
            yield voltmeter.set_active_channels(VOLTMETER_CHANNELS)
            yield voltmeter.set_sampling_duration(SAMPLING_DURATION)
            yield voltmeter.set_triggering(False)            
        
        def update_plot(plot,sample):
            t = traces[plot]
            t.insert(0,sample)
            t.pop()
            plots[plot].setData(t)

        def get_setpoint():
            return temperature_setpoint_spin.value()

        def get_rate_setpoint(temperature):
            temperature_setpoint = get_setpoint()
            delta_temperature = temperature_setpoint - temperature
            if abs(delta_temperature) > TEMPERATURE_BUFFER:
                return MAX_RAMP_RATE * (
                    1 if delta_temperature > 0 else -1
                )
            else:
                return MAX_RAMP_RATE * delta_temperature / TEMPERATURE_BUFFER

        @inlineCallbacks
        def loop():
            packet = voltmeter.packet()
            for channel in VOLTMETER_CHANNELS:                
                packet.get_sample(channel,key=channel)
            samples = yield packet.send()
            time = clock()
            temperature, emission = samples[TEMPERATURE_CHANNEL], samples[EMISSION_CHANNEL]
            update_plot(FILAMENT_TRACE,self.previous_filament_control)
            update_plot(EMISSION_TRACE,emission)
            update_plot(TEMPERATURE_TRACE,temperature)
            temperature_setpoint = get_setpoint()
            update_plot(TEMPERATURE_SETPOINT_TRACE,temperature_setpoint)
            rate_setpoint = get_rate_setpoint(temperature)
            update_plot(RATE_SETPOINT_TRACE,rate_setpoint)
            ramp_rate = ( temperature - self.previous_temperature ) / SAMPLING_DURATION
            update_plot(RATE_TRACE,ramp_rate)
            filament_control = self.previous_filament_control + DELTA_CONTROL * (1 if ramp_rate < rate_setpoint else -1)

            yield analog_output.set_value(FILAMENT_CHANNEL,filament_control)            
            yield data_vault.add(
                [
                    {
                        TIME:time,
                        FILAMENT_CONTROL:filament_control,
                        EMISSION_CURRENT:emission,
                        TEMPERATURE:temperature,
                        TEMPERATURE_SETPOINT:temperature_setpoint,
                        RATE:ramp_rate,
                        RATE_SETPOINT:rate_setpoint
                    }[key] for key in INPUTS + OUTPUTS
                ]
            )
            self.previous_temperature = temperature
            self.previous_filament_control = filament_control
            self.previous_time = time            
            if self.stop_requested:
                self.stop_requested = False
            else:
                loop()

        @inlineCallbacks
        def init_loop():
            yield init_voltmeter()
            self.previous_temperature = yield voltmeter.get_sample(TEMPERATURE_CHANNEL)            
            self.previous_filament_control = yield analog_output.get_value(FILAMENT_CHANNEL)
            self.previous_time = clock()

        self.stop_requested = False

        @inlineCallbacks
        def on_run():
            if self.stop_requested:
                returnValue(None)
            if run_check.isChecked():
                yield init_loop()
                loop()
            else:
                self.stop_requested = True
        run_check.clicked.connect(on_run)

    def closeEvent(self,event):
        if reactor.running:
            reactor.stop()
        event.accept()

if __name__ == '__main__':
    def main():
        heater_widget = HeaterWidget()
        container.append(heater_widget)
        heater_widget.show()
    container = []
    reactor.callWhenRunning(main)
    reactor.run()
