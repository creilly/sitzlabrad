from deviceserver import DeviceServer, Device, device_setting, DeviceSignal
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
import labrad
from steppermotor import DigitalStepperMotor, CounterStepperMotor, RampStepperMotor, SetPositionStoppedException, DisabledException
from daqmx.task.do import DOTask
from daqmx.task.co import COTask
from daqmx.task.ci import CITask
from twisted.internet.threads import deferToThread

"""
### BEGIN NODE INFO
[info]
name = Stepper Motor
version = 1.0
description = provides access to all stepper motors
[startup]
cmdline = %PYTHON% %FILE%
timeout = 20
[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

NAME = 'Stepper Motor'
REGISTRY_PATH = ['','Servers',NAME]

DIR_CHANNEL = 'direction channel'
INIT_POS = 'initial position'

ENABLE_CHANNEL = 'enable channel'

CLASS = 'class'
DIGITAL = 'digital'
COUNTER = 'counter'
RAMP = 'ramp'

STEP_CHANNEL = 'step channel' # step output channel for digital stepper motors, step input for ramp stepper motors
DELAY = 'delay'

STEP_OUTPUT_CHANNEL = 'step output channel'
STEP_INPUT_CHANNEL = 'step input channel'

RSM_ID = 'rsm id'
STOP_CHANNEL = 'stop channel'

ON_NEW_POSITION = 'on new position'
ON_BUSY_STATUS_CHANGED = 'on busy status changed'
ON_ENABLED_STATUS_CHANGED = 'on enabled status changed'

UPDATE_INTERVAL = .1

class StepperMotorBusyException(Exception): pass

class StepperMotorDevice(Device):

    on_new_position = DeviceSignal(110,ON_NEW_POSITION,'i')
    on_busy_status_changed = DeviceSignal(111,ON_BUSY_STATUS_CHANGED,'b')
    on_enabled_status_changed = DeviceSignal(112,ON_ENABLED_STATUS_CHANGED,'b')

    def __init__(self,sm,sm_name,client):
        Device.__init__(self)
        self.sm = sm
        self.sm_name = sm_name
        self.busy = False
        self.client = client

    @device_setting(11,device_setting_lockable=True,position='i')    
    def set_position(self,c,position):
        if self.get_busy_status():
            raise StepperMotorBusyException
        sm = self.sm
        old_position = sm.get_position()
        self.set_busy_status(True)
        try:
            def update_position(_):
                if self.get_busy_status():
                    self.on_new_position(
                        old_position + {
                            sm.FORWARDS:1,
                            sm.BACKWARDS:-1
                        }[sm.get_direction()]*sm.get_pulses()
                    )
                    reactor.callLater(
                        UPDATE_INTERVAL,
                        update_position,
                        None
                    )
            reactor.callLater(
                UPDATE_INTERVAL,
                update_position,
                None
            )
            yield deferToThread(
                sm.set_position,
                position
            )
            failed = False
        except (SetPositionStoppedException,DisabledException), e:
            failed = True
        new_position = sm.get_position()
        self.set_busy_status(False)
        reg = self.client.registry
        yield reg.cd(REGISTRY_PATH+[self.sm_name])
        yield reg.set(INIT_POS,int(new_position))
        self.on_new_position(new_position)
        if failed:
            raise e

    @device_setting(12,returns='i')
    def get_position(self,c):
        return self.sm.get_position()
    
    @device_setting(13,returns='b')
    def is_busy(self,c):
        return self.get_busy_status()

    @device_setting(14)
    def stop(self,c):
        self.sm.stop()

    @device_setting(15,returns='b')
    def is_enabled(self,c):
        return self.sm.is_enabled()

    @device_setting(16,is_enabled='b')
    def set_enabled(self,c,is_enabled):
        self.sm.set_enabled(is_enabled)
        self.on_enabled_status_changed(is_enabled)

    @device_setting(17,returns='b')
    def is_enableable(self,c):
        return self.sm.is_enableable()

    def get_busy_status(self):
        return self.busy
    
    def set_busy_status(self,busy_status):
        self.busy = busy_status
        self.on_busy_status_changed(busy_status)            

class StepperMotorServer(DeviceServer):
    name = NAME    # Will be labrad name of server
    device_class = StepperMotorDevice
    sendTracebacks = True

    @inlineCallbacks
    def initServer(self):  # Do initialization here
        reg = self.client.registry
        yield reg.cd(REGISTRY_PATH)
        stepper_motor_names = yield reg.dir()
        stepper_motor_names = stepper_motor_names[0] # just get directories
        self.stepper_motors = {name:None for name in stepper_motor_names}
        for stepper_motor_name in stepper_motor_names:
            yield self.add_stepper_motor(stepper_motor_name)
        yield DeviceServer.initServer(self)

    @inlineCallbacks
    def add_stepper_motor(self,stepper_motor_name):
        reg = self.client.registry
        yield reg.cd(REGISTRY_PATH+[stepper_motor_name])
        
        dirs, keys = yield reg.dir()
        dir_channel = yield reg.get(DIR_CHANNEL)
        dir_task = DOTask(dir_channel)
        
        init_pos = yield reg.get(INIT_POS)        
        
        if ENABLE_CHANNEL in keys:
            enable_channel = yield reg.get(ENABLE_CHANNEL)
            enable_task = DOTask(enable_channel)
        else:
            enable_task = None

        if CLASS in keys:
            class_type = yield reg.get(CLASS)
        else:
            class_type = DIGITAL
        if class_type == DIGITAL:
            step_channel = yield reg.get(STEP_CHANNEL)
            step_task = DOTask(step_channel)
            
            delay = yield reg.get(DELAY)
            
            sm = DigitalStepperMotor(
                step_task,
                delay,                
                dir_task,
                enable_task,
                init_pos
            )
        if class_type == COUNTER:
            step_output_channel = yield reg.get(STEP_OUTPUT_CHANNEL)
            step_output_task = COTask(step_output_channel)
            step_input_channel = yield reg.get(STEP_INPUT_CHANNEL)
            step_input_task = CITask(step_input_channel)
            
            sm = CounterStepperMotor(
                step_output_task,
                step_input_task,
                dir_task,
                enable_task,
                init_pos,
            )
        if class_type == RAMP:
            rsm_id = yield reg.get(RSM_ID)

            stop_channel = yield reg.get(STOP_CHANNEL)
            stop_task = DOTask(stop_channel)

            step_channel = yield reg.get(STEP_CHANNEL)
            step_task = CITask(step_channel)
            
            sm = RampStepperMotor(
                rsm_id,
                stop_task,
                step_task,
                dir_task,
                enable_task,
                init_pos
            )                

        self.add_device(
            stepper_motor_name,
            StepperMotorDevice(sm,stepper_motor_name,self.client)
        )

__server__ = StepperMotorServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
