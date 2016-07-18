from labrad.server import LabradServer, setting, Signal
from twisted.internet.defer import inlineCallbacks, Deferred
import labrad
import numpy as np
from functools import partial
from time import clock

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

FEEDBACK_ON, FEEDBACK_OFF = 'feedback on', 'feedback off'
FEEDBACK_STATES = (FEEDBACK_ON,FEEDBACK_OFF)

COOLING, HEATING = 'cooling','heating'
HEATING_STATES = (COOLING,HEATING)

BELOW, ABOVE = 'below','above'
LIMIT_STATES = (BELOW,ABOVE)

OK, FAILED = 'ok','failed'
THERMOCOUPLE_STATES = (OK,FAILED)

TEMPERATURE, EMISSION_CURRENT = 'sample temperature', 'emission current'
VOLTMETER_CHANNELS = (TEMPERATURE,EMISSION_CURRENT)

FILAMENT_CONTROL = 'filament control output'

class HeaterServer(LabradServer):
    name = NAME

    on_feedback_state_changed = Signal(110,ON_FEEDBACK_STATE_CHANGED,'s')
    on_heating_state_changed = Signal(111,ON_HEATING_STATE_CHANGED,'s')
    on_temperature_setpoint_changed = Signal(112,ON_TEMPERATURE_SETPOINT_CHANGED,'v')
    on_temperature_limit_state_changed = Signal(113,ON_TEMPERATURE_LIMIT_CHANGED,'s')
    on_emission_current_limit_state_changed = Signal(114,ON_EMISSION_CURRENT_LIMIT_STATE_CHANGED,'s')
    on_thermocouple_state_changed = Signal(115,ON_THERMOCOUPLE_STATE_CHANGED,'s')

    @inlineCallbacks
    def get_outputs(self):
        voltmeter = self.client.voltmeter
        packet = voltmeter.packet()
        for channel in VOLTMETER_CHANNELS:                
            packet.get_sample(channel,key=channel)
        samples = yield packet.send()
        return samples

    def get_filament_control(self):
        ao = self.client.analog_output
        return ao.get_value(FILAMENT_CONTROL)

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
        reg = self.client.registry
        reg.cd(REGISTRY_PATH)
        self.emission_limit = yield reg.get('emission current limit')
        self.temperature_limit = yield reg.get('temperature limit')
        self.thermocouple_failure_limit = yield reg.get('thermocouple failure limit')
        self.ramp_rate = yield reg.get('ramp rate')
        self.filament_control_increment = yield reg.get('filament control increment')
        self.temperature_buffer = yield reg.get('temperature buffer')
        sampling_duration = yield reg.get('sampling duration')
        cm = ConnectionManager(self.client.manager)
        required_servers = [VM_SERVER,AO_SERVER]
        servers = yield cm.get_connected_servers()
        for server in servers:
            if server in required_servers:
                required_servers.remove(server)
        @inlineCallbacks
        def finish_init():
            voltmeter = self.client.voltmeter
            voltmeter.set_sampling_duration(sampling_duration)
            voltmeter.set_active_channels(OUTPUTS)
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
            LabradServer.initServer(self)
        def on_server_connected(server):
            required_servers.remove(server)
            cm.on_server_connect(server,None)
            if not required_servers:
                finish_init()
        if required_servers:
            for server in required_servers:
                cm.on_server_connect(server,partial(on_server_connected,server))                
        else:
            finish_init()

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
        if ABOVE in (self.emission_current_limit_state,self.temperature_limit_state):
            filament_control = yield self.decrease_filament_control()
        elif self.feedback_state == FEEDBACK_ON:
            filament_control = yield self.close_control_loop(temperature,rate)
        else:
            filament_control = yield self.get_filament_control()
        while self.update_requests:
            update_type, callback = self.update_requests.pop()
            if update_type == FILAMENT_CONTROL_UPDATE:
                callback(filament_control)
            elif update_type == EMISSION_CURRENT_UPDATE:
                callback(emission_current)
            elif update_type == TEMPERATURE_UPDATE:
                callback(temperature)
            elif update_type == RATE_UPDATE:
                callback(rate)
        indices_to_remove = []
        for index, trigger_request in enumerate(self.trigger_requests):
            temperature_threshold, slope, callback = trigger_request
            if (
                    (
                        slope == RISING and temperature > temperature_threshold
                    ) or (
                        slope == FALLING and temperature < temperature_threshold:
                    )
            ):                        
                callback()
                indices_to_remove.append(index)
        for index in reversed(indices_to_remove):
            self.trigger_requests.remove(index)                

    def get_rate_setpoint(self,temperature):
        if self.heating_state == COOLING:
            return -1. * self.ramp_rate
        else:
            delta_temperature = self.temperature_setpoint - temperature
            if abs(delta_temperature) > self.temperature_buffer:
                return self.ramp_rate * (1. if delta_temperature > 0 else -1.)
            else:
                return self.ramp_rate * delta_temperature / self.temperature_buffer

    @inlineCallbacks
    def close_control_loop(self,temperature,rate):
        rate_setpoint = self.get_rate_setpoint(temperature)
        if rate < rate_setpoint:
            filament_control = yield self.increase_filament_control()
        else:
            filament_control = yield self.decrease_filament_control()
        returnValue(filament_control)

    def request_update(self,update_code):
        d = Deferred()
        self.update_requests.append(
            (
                update_code,
                d.callback
            )
        )
        return d

    @setting(10, returns='s')
    def get_feedback_state(self,c):
        return self._get_feedback_state()
    
    @setting(11, feedback_state='s')  
    def set_feedback_state(self,c,feedback_state):
        self._set_feedback_state(feedback_state)

    @setting(12, returns='s')
    def get_heating_state(self,c):
        return self._get_heating_state()

    @setting(13, heating_state='s')          
    def set_heating_state(self,c,heating_state):
        self._set_heating_state(heating_state)

    @setting(14, returns='v')
    def get_filament_control(self):
        return self.request_update(FILAMENT_CONTROL_UPDATE)

    @setting(15, returns='v')
    def get_emission_current(self):
        return self.request_update(EMISSION_CONTROL_UPDATE)

    @setting(16, returns='v')
    def get_temperature(self):
        return self.request_update(TEMPERATURE_UPDATE)

    @setting(17, returns='v')
    def get_rate(self):
        return self.request_update(RATE_UPDATE)
    
__server__ = AnalogOutputServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
