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
from qtutils.labraderror import catch_labrad_error
from qtutils.lockwidget import LockWidget
from qtutils.labelwidget import LabelWidget

pg.setConfigOption('background','w')
pg.setConfigOption('foreground','k')

MIN_TEMPERATURE, MAX_TEMPERATURE = 0, 1150
RUNNING_AVERAGE = 40 # samples (i.e. 40 -> 2 second running average at 50ms per sample)
HISTORY = 400
TIME = 'time'
INPUTS = (TIME,)
FILAMENT_CONTROL, EMISSION_CURRENT, TEMPERATURE, TEMPERATURE_SETPOINT, RATE, RATE_AVERAGE, RATE_SETPOINT = 'filament control', 'emission current', 'temperature', 'temperature setpoint', 'rate', 'rate average', 'rate setpoint'
OUTPUTS = (FILAMENT_CONTROL,EMISSION_CURRENT,TEMPERATURE,TEMPERATURE_SETPOINT,RATE,RATE_AVERAGE,RATE_SETPOINT)
FILAMENT_PW, EMISSION_PW, TEMPERATURE_PW, RATE_PW = 0,1,2,3
PLOTS = (FILAMENT_PW,EMISSION_PW,TEMPERATURE_PW,RATE_PW)
TITLE, TRACES, LABEL = 0,1,2
FILAMENT_TRACE,EMISSION_TRACE,TEMPERATURE_TRACE,TEMPERATURE_SETPOINT_TRACE,RATE_TRACE,RATE_SETPOINT_TRACE = 0,1,2,3,4,5
TRACE_NAME, TRACE_TYPE = 0,1
TRACE_ATTRS = (TRACE_NAME,TRACE_TYPE)
LINE, SCATTER = 0,1
PLOTS_DICT = {
    FILAMENT_PW:{
        TITLE:'filament control',
        TRACES:{
            FILAMENT_TRACE:{
                TRACE_NAME:'filament control',
                TRACE_TYPE:SCATTER
            }
        },
        LABEL:'control voltage (volts)'
    },
    EMISSION_PW:{
        TITLE:'emission current',
        TRACES:{
            EMISSION_TRACE:{
                TRACE_NAME:'emission current',
                TRACE_TYPE:SCATTER
            }
        },
        LABEL:'emission current (mA)'
    },
    TEMPERATURE_PW:{
        TITLE:'sample temperature',
        TRACES:{
            TEMPERATURE_TRACE:{
                TRACE_NAME:'temperature',
                TRACE_TYPE:SCATTER
            },
            TEMPERATURE_SETPOINT_TRACE:{
                TRACE_NAME:'setpoint',
                TRACE_TYPE:LINE
            }
        },
        LABEL:'temperature (degs celsius)'
    },
    RATE_PW:{
        TITLE:'temperature ramp rate',
        TRACES:{
            RATE_TRACE:{
                TRACE_NAME:'ramp rate',
                TRACE_TYPE:SCATTER
            },
            RATE_AVERAGE:{
                TRACE_NAME:'average',
                TRACE_TYPE:LINE
            },
            RATE_SETPOINT_TRACE:{
                TRACE_NAME:'ramp rate setpoint',
                TRACE_TYPE:LINE
            }
        },
        LABEL:'temperature velocity (degs c/second)'
    }
}

class HeaterWidget(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.init_widget()

    @inlineCallbacks
    def init_widget(self):
        layout = QtGui.QHBoxLayout()
        self.setLayout(layout)

        plot_layout = QtGui.QHBoxLayout()
        layout.addLayout(plot_layout)

        plots = {}        
        traces = {}
        for plot in PLOTS:
            plot_dict = PLOTS_DICT[plot]
            plot_widget = PlotWidget(
                title=plot_dict[TITLE],
                labels={
                    'bottom':'time (samples)',
                    'left':plot_dict[LABEL]
                }
            )
            plot_traces = plot_dict[TRACES]            
            if len(plot_traces) > 1:
                plot_widget.addLegend()
            trace_index = 0
            colors = ('F33','3F3','33F')
            for trace_key, trace_d in plot_traces.items():
                trace = [0] * HISTORY
                kwargs = {
                    LINE:{
                        'pen':{'color':colors[trace_index]}
                    },
                    SCATTER:{
                        'pen':None,
                        'symbol':'o',
                        'symbolSize':3,
                        'symbolBrush':colors[trace_index]
                    }                   
                }[trace_d[TRACE_TYPE]]
                kwargs['name'] = trace_d[TRACE_NAME]
                plot = plot_widget.plot(
                    trace,
                    **kwargs
                )
                plots[trace_key] = plot
                traces[trace_key] = trace
                trace_index += 1
            plot_layout.addWidget(plot_widget)

        client = yield connectAsync()
        sh_server = client.sample_heater

        controls_layout = QtGui.QVBoxLayout()
        layout.addLayout(controls_layout)

        temperature_setpoint_layout = QtGui.QHBoxLayout()
        
        controls_layout.addWidget(
            LabelWidget(
                'temperature setpoint',
                temperature_setpoint_layout
            )
        )

        temperature_setpoint_label = QtGui.QLabel()
        temperature_setpoint_layout.addWidget(temperature_setpoint_label)

        temperature_setpoint_layout.addStretch()
            
        temperature_setpoint_spin = QtGui.QSpinBox()
        temperature_setpoint_spin.setRange(MIN_TEMPERATURE,MAX_TEMPERATURE)
        temperature_setpoint_spin.setPrefix('temp')
        temperature_setpoint_spin.setSuffix('C')
        temperature_setpoint_layout.addWidget(temperature_setpoint_spin)

        temperature_setpoint_button = QtGui.QPushButton('set')
        temperature_setpoint_layout.addWidget(temperature_setpoint_button)

        def set_temperature_setpoint():
            catch_labrad_error(
                self,
                sh_server.set_temperature_setpoint(temperature_setpoint_spin.value())
            )
        temperature_setpoint_button.clicked.connect(set_temperature_setpoint)        

        def update_temperature_setpoint(temperature_setpoint):
            self.temperature_setpoint = temperature_setpoint
            temperature_setpoint_label.setText('temp setpoint: %d' % self.temperature_setpoint)            

        sh_server.on_temperature_setpoint_changed.connect(
            lambda c, temperature_setpoint: update_temperature_setpoint(temperature_setpoint)
        )
        temperature_setpoint = yield sh_server.get_temperature_setpoint()
        update_temperature_setpoint(temperature_setpoint)

        def update_label(label,state):
            label.setText('status: ' + str(state))

        for name, signal, getter, setter, option_1, option_2 in (
                (
                    'heating state',
                    sh_server.on_heating_state_changed,
                    sh_server.get_heating_state,
                    sh_server.set_heating_state,
                    'heating',
                    'cooling'
                ),
                (
                    'feedback state',
                    sh_server.on_feedback_state_changed,
                    sh_server.get_feedback_state,
                    sh_server.set_feedback_state,
                    True,
                    False
                ),
                (
                    'temperature limit state',
                    sh_server.on_temperature_limit_state_changed,
                    sh_server.get_temperature_limit_state,
                    None,
                    None,
                    None
                ),
                (
                    'emission current limit state',
                    sh_server.on_emission_current_limit_state_changed,
                    sh_server.get_emission_current_limit_state,
                    None,
                    None,
                    None
                ),
                (
                    'thermocouple state',
                    sh_server.on_thermocouple_state_changed,
                    sh_server.get_thermocouple_state,
                    None,
                    None,
                    None
                ),
                
        ):
            layout = QtGui.QHBoxLayout()            
            controls_layout.addWidget(
                LabelWidget(
                    name,
                    layout
                )
            )
            
            label = QtGui.QLabel()
            layout.addWidget(label)
            
            layout.addStretch()
            
            state = yield getter()
            update_label(label,state)

            def get_slot(label):
                def slot(c,state):
                    update_label(label,state)
                return slot
            signal.connect(get_slot(label))

            if setter is None: continue

            def cb(setter,option):
                catch_labrad_error(
                    self,
                    setter(option)
                )
            for option in (option_1,option_2):
                button = QtGui.QPushButton(str(option))
                layout.addWidget(button)
                button.clicked.connect(partial(cb,setter,option))
        
        for lockable_setting in (
                sh_server.set_feedback_state,
                sh_server.set_heating_state,
                sh_server.set_temperature_setpoint
        ):
            controls_layout.addWidget(LockWidget(sh_server,lockable_setting.ID,lockable_setting.name))

        def update_plot(plot,sample):
            t = traces[plot]
            t.insert(0,sample)
            t.pop()
            plots[plot].setData(t)
            
        @inlineCallbacks
        def loop():
            packet = sh_server.packet()
            packet.get_filament_control()
            packet.get_emission_current()
            packet.get_temperature()
            packet.get_rate()
            packet.get_rate_setpoint()
            
            result = yield packet.send()
            
            filament_control = result.get_filament_control
            update_plot(FILAMENT_TRACE,filament_control)
            
            temperature = result.get_temperature
            update_plot(TEMPERATURE_TRACE,temperature)
            
            emission_current = result.get_emission_current
            update_plot(EMISSION_TRACE,emission_current)
            
            rate = result.get_rate
            update_plot(RATE_TRACE,rate)
            
            rate_setpoint = result.get_rate_setpoint
            update_plot(RATE_SETPOINT_TRACE,rate_setpoint)

            temperature_setpoint = self.temperature_setpoint
            update_plot(TEMPERATURE_SETPOINT_TRACE,temperature_setpoint)            

            rate_average = np.average(traces[RATE_TRACE][:RUNNING_AVERAGE])
            update_plot(RATE_AVERAGE,rate_average)
            
            loop()

        loop()

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
