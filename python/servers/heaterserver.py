from lockserver import LockServer, lockable_setting
from labrad.server import setting, Signal
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue
import labrad
import numpy as np
from functools import partial
from time import clock
from labrad.types import Error
from connectionmanager import ConnectionManager

"""
### BEGIN NODE INFO
[info]
name = Sample Heater
version = 1.0
description = controls sample heater
[startup]
cmdline = %PYTHON% %FILE%
timeout = 20
[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

NAME = 'Sample Heater'
REGISTRY_PATH = ['','Servers',NAME]

VM_SERVER, AO_SERVER = 'Voltmeter', 'Analog Output'

ON_FEEDBACK_STATE_CHANGED = 'on_feedback_state_changed'
ON_HEATING_STATE_CHANGED = 'on_heating_state_changed'
ON_TEMPERATURE_SETPOINT_CHANGED = 'on_temperature_setpoint_changed'
ON_TEMPERATURE_LIMIT_STATE_CHANGED = 'on_temperature_limit_state_changed'
ON_EMISSION_CURRENT_LIMIT_STATE_CHANGED = 'on_emission_current_limit_state_changed'
ON_THERMOCOUPLE_STATE_CHANGED = 'on_thermocouple_state_changed'

FEEDBACK_ON, FEEDBACK_OFF = True, False
FEEDBACK_STATES = (FEEDBACK_ON,FEEDBACK_OFF)

COOLING, HEATING = 'cooling','heating'
HEATING_STATES = (COOLING,HEATING)

BELOW, ABOVE = 'below','above'
LIMIT_STATES = (BELOW,ABOVE)

OK, FAILED = 'ok','failed'
THERMOCOUPLE_STATES = (OK,FAILED)

TEMPERATURE, EMISSION_CURRENT, AUGER_INPUT, QMS_INPUT = 'sample temperature', 'emission current', 'auger input', 'qms input'
VOLTMETER_CHANNELS = (TEMPERATURE,EMISSION_CURRENT,AUGER_INPUT,QMS_INPUT)

FILAMENT_CONTROL = 'filament control output'

FILAMENT_CONTROL_UPDATE, EMISSION_CURRENT_UPDATE, TEMPERATURE_UPDATE, RATE_UPDATE, RATE_SETPOINT_UPDATE = 0,1,2,3,4

NUDGE_UP, NUDGE_DOWN = 0, 1

class HeaterServer(LockServer):
    name = NAME

    on_feedback_state_changed = Signal(110,ON_FEEDBACK_STATE_CHANGED,'b')
    on_heating_state_changed = Signal(111,ON_HEATING_STATE_CHANGED,'s')
    on_temperature_setpoint_changed = Signal(112,ON_TEMPERATURE_SETPOINT_CHANGED,'v')
    on_temperature_limit_state_changed = Signal(113,ON_TEMPERATURE_LIMIT_STATE_CHANGED,'s')
    on_emission_current_limit_state_changed = Signal(114,ON_EMISSION_CURRENT_LIMIT_STATE_CHANGED,'s')
    on_thermocouple_state_changed = Signal(115,ON_THERMOCOUPLE_STATE_CHANGED,'s')

    @inlineCallbacks
    def get_outputs(self):
        voltmeter = self.client.voltmeter
        packet = voltmeter.packet()
        for channel in VOLTMETER_CHANNELS:                
            packet.get_sample(channel,key=channel)
        samples = yield packet.send()
        returnValue(samples)

    def _get_filament_control(self):
        ao = self.client.analog_output
        return ao.get_value()

    def set_filament_control(self,filament_control):
        ao = self.client.analog_output
        return ao.set_value(filament_control)

    def update_temperature_limit_state(self,temperature):
        self._set_temperature_limit_state(
            BELOW
            if temperature < self._get_temperature_limit() else
            ABOVE
        )

    def _get_temperature_limit(self):
        return self.temperature_limit
        
    def _get_temperature_limit_state(self):
        return self.temperature_limit_state

    def _set_temperature_limit_state(self,temperature_limit_state):
        prev_state = self._get_temperature_limit_state()
        new_state = temperature_limit_state
        if new_state != prev_state:
            self.temperature_limit_state = new_state
            self.on_temperature_limit_state_changed(new_state)

    def update_emission_current_limit_state(self,emission_current):
        self._set_emission_current_limit_state(
            BELOW
            if emission_current < self._get_emission_current_limit() else
            ABOVE
        )

    def _get_emission_current_limit(self):
        return self.emission_current_limit

    def _get_emission_current_limit_state(self):
        return self.emission_current_limit_state

    def _set_emission_current_limit_state(self,emission_current_limit_state):
        prev_state = self._get_emission_current_limit_state()
        new_state = emission_current_limit_state        
        if new_state != prev_state:
            self.emission_current_limit_state = new_state
            self.on_emission_current_limit_state_changed(new_state)

    def update_thermocouple_state(self,temperature):
        self._set_thermocouple_state(
            OK
            if abs(temperature) < self._get_thermocouple_failure_limit() else
            FAILED
        )

    def _get_thermocouple_failure_limit(self):
        return self.thermocouple_failure_limit

    def _get_thermocouple_state(self):
        return self.thermocouple_state

    def _set_thermocouple_state(self,thermocouple_state):
        prev_state = self._get_thermocouple_state()
        new_state = thermocouple_state
        if new_state != prev_state:
            self.thermocouple_state = new_state
            self.on_thermocouple_state_changed(new_state)

    @inlineCallbacks
    def initServer(self):
        self.update_requests = []
        self.trigger_requests = []
        self.temperature_limit_state = BELOW
        self.emission_current_limit_state = BELOW
        self.thermocouple_state = OK

        reg = self.client.registry
        reg.cd(REGISTRY_PATH)
        self.emission_current_limit = yield reg.get('emission current limit')
        self.temperature_limit = yield reg.get('temperature limit')
        self.thermocouple_failure_limit = yield reg.get('thermocouple failure limit')
        self.ramp_rate = yield reg.get('ramp rate')
        self.cooling_ramp_rate = yield reg.get('cooling ramp rate')
        self.filament_control_increment = yield reg.get('filament control increment')
        self.filament_control_fast_increment = yield reg.get('filament control fast increment')
        self.filament_control_threshold = yield reg.get('filament control threshold')
        self.emission_current_threshold = yield reg.get('emission current threshold')
        self.temperature_buffer = yield reg.get('temperature buffer')
        default_temperature_setpoint = yield reg.get('default temperature')
        self._set_temperature_setpoint(default_temperature_setpoint)
        sampling_duration = yield reg.get('sampling duration')
        cm = ConnectionManager(self.client.manager)
        required_servers = [VM_SERVER,AO_SERVER]
        servers = yield cm.get_connected_servers()
        for server in servers:
            if server in required_servers:
                print server, 'connected'
                required_servers.remove(server)
        @inlineCallbacks
        def finish_init():
            voltmeter = self.client.voltmeter
            yield voltmeter.lock_setting(voltmeter.set_active_channels.ID)
            yield voltmeter.lock_setting(voltmeter.set_sampling_duration.ID)
            yield voltmeter.lock_setting(voltmeter.set_triggering.ID)
            yield voltmeter.set_sampling_duration(sampling_duration)
            yield voltmeter.set_active_channels(VOLTMETER_CHANNELS)
            yield voltmeter.set_triggering(False)
            analog_output = self.client.analog_output
            yield analog_output.select_device(FILAMENT_CONTROL)
            yield analog_output.lock()
            self._set_feedback_state(FEEDBACK_OFF)
            self._set_heating_state(COOLING)
            outputs = yield self.get_outputs()
            self.previous_time = clock()
            temperature = self.previous_temperature = outputs[TEMPERATURE]
            emission_current = outputs[EMISSION_CURRENT]
            self.update_temperature_limit_state(temperature)
            self.update_emission_current_limit_state(emission_current)
            self.update_thermocouple_state(temperature)
            self.loop()
            LockServer.initServer(self)
        def on_server_connected(server):
            print server, 'connected'
            required_servers.remove(server)
            cm.on_server_connect(server,None)
            if not required_servers:
                finish_init()
        if required_servers:
            for server in required_servers:
                print 'waiting for', server
                cm.on_server_connect(server,partial(on_server_connected,server))
        else:
            yield finish_init()

    @inlineCallbacks
    def loop(self):
        outputs = yield self.get_outputs()
        time = clock()
        temperature, emission_current = outputs[TEMPERATURE], outputs[EMISSION_CURRENT]
        self.update_temperature_limit_state(temperature)
        self.update_emission_current_limit_state(emission_current)
        self.update_thermocouple_state(temperature)
        rate = ( temperature - self.previous_temperature ) / ( time - self.previous_time )
        self.previous_temperature = temperature
        self.previous_time = time
        if (
                ABOVE in (self.emission_current_limit_state,self.temperature_limit_state)
                or
                FAILED == self.thermocouple_state
        ):
            filament_control = yield self.decrease_filament_control(emission_current)
        elif self.feedback_state == FEEDBACK_ON:
            filament_control = yield self.close_control_loop(emission_current,temperature,rate)
        else:
            filament_control = yield self._get_filament_control()
        while self.update_requests:
            update_type, d = self.update_requests.pop()
            if update_type == FILAMENT_CONTROL_UPDATE:
                d.callback(filament_control)
            elif update_type == EMISSION_CURRENT_UPDATE:
                d.callback(emission_current)
            elif update_type == TEMPERATURE_UPDATE:
                d.callback(temperature)
            elif update_type == RATE_UPDATE:
                d.callback(rate)
            elif update_type == RATE_SETPOINT_UPDATE:
                d.callback(self._get_rate_setpoint(temperature))
        indices_to_remove = []
        for index, trigger_request in enumerate(self.trigger_requests):
            temperature_threshold, slope, d = trigger_request
            if (
                    (
                        slope == RISING and temperature > temperature_threshold
                    ) or (
                        slope == FALLING and temperature < temperature_threshold
                    )
            ):                        
                d.callback()
                indices_to_remove.append(index)
        for index in reversed(indices_to_remove):
            self.trigger_requests.remove(index)                
        self.loop()

    def _get_rate_setpoint(self,temperature):
        if self.heating_state == COOLING:
            return -1. * self.cooling_ramp_rate
        else:
            delta_temperature = self.temperature_setpoint - temperature
            if abs(delta_temperature) > self.temperature_buffer:
                return self.ramp_rate * (1. if delta_temperature > 0 else -1.)
            else:
                return self.ramp_rate * delta_temperature / self.temperature_buffer

    def _set_temperature_setpoint(self,temperature_setpoint):
        self.temperature_setpoint = temperature_setpoint
        self.on_temperature_setpoint_changed(temperature_setpoint)

    @inlineCallbacks
    def close_control_loop(self,emission_current,temperature,rate):
        rate_setpoint = self._get_rate_setpoint(temperature)
        if rate < rate_setpoint:
            filament_control = yield self.increase_filament_control(emission_current)
        else:
            filament_control = yield self.decrease_filament_control(emission_current)
        returnValue(filament_control)

    def increase_filament_control(self,emission_current):
        return self.nudge_filament_control(emission_current,NUDGE_UP)
        
    def decrease_filament_control(self,emission_current):
        return self.nudge_filament_control(emission_current,NUDGE_DOWN)

    @inlineCallbacks
    def nudge_filament_control(self,emission_current,nudge_direction):
        old_filament_control = yield self._get_filament_control()
        increment = (
            self.filament_control_fast_increment
            if (
                    emission_current < self.emission_current_threshold
                    and
                    old_filament_control < self.filament_control_threshold
            ) else
            self.filament_control_increment
        )
        new_filament_control = old_filament_control + {
            NUDGE_UP:1,
            NUDGE_DOWN:-1
        }[nudge_direction]*increment
        if new_filament_control < 0:
            new_filament_control = 0.
        yield self.set_filament_control(new_filament_control)
        filament_control = yield self._get_filament_control()
        returnValue(filament_control)

    def request_update(self,update_code):
        d = Deferred()
        self.update_requests.append(
            (
                update_code,
                d
            )
        )
        return d

    def _set_feedback_state(self,feedback_state):
        self.feedback_state = feedback_state
        self.on_feedback_state_changed(feedback_state)

    def _set_heating_state(self,heating_state):
        self.heating_state=heating_state
        self.on_heating_state_changed(heating_state)

    @setting(10, returns='b')
    def get_feedback_state(self,c):
        return self.feedback_state
        
    @lockable_setting(11, feedback_state='b')  
    def set_feedback_state(self,c,feedback_state):
        self._set_feedback_state(feedback_state)

    @setting(12, returns='s')
    def get_heating_state(self,c):
        return self.heating_state

    @lockable_setting(13, heating_state='s')          
    def set_heating_state(self,c,heating_state):
        self._set_heating_state(heating_state)

    @setting(14, returns='v')
    def get_filament_control(self,c):
        return self.request_update(FILAMENT_CONTROL_UPDATE)

    @setting(15, returns='v')
    def get_emission_current(self,c):
        return self.request_update(EMISSION_CURRENT_UPDATE)

    @setting(16, returns='v')
    def get_temperature(self,c):
        return self.request_update(TEMPERATURE_UPDATE)

    @setting(17, returns='v')
    def get_rate(self,c):
        return self.request_update(RATE_UPDATE)

    @setting(18, returns='v')
    def get_rate_setpoint(self,c):
        return self.request_update(RATE_SETPOINT_UPDATE)

    @setting(19, returns='v')
    def get_temperature_setpoint(self,c):
        return self.temperature_setpoint

    @lockable_setting(20, temperature_setpoint='v')
    def set_temperature_setpoint(self,c,temperature_setpoint):
        self._set_temperature_setpoint(temperature_setpoint)

    @setting(21,returns='s')
    def get_temperature_limit_state(self,c):
        return self._get_temperature_limit_state()

    @setting(22,returns='s')
    def get_emission_current_limit_state(self,c):
        return self._get_emission_current_limit_state()

    @setting(23,returns='s')
    def get_thermocouple_state(self,c):
        return self._get_thermocouple_state()
    
__server__ = HeaterServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
