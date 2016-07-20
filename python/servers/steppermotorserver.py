from labrad.server import LabradServer, setting, Signal
from lockserver import LockServer, lockable_setting
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
import labrad
from steppermotor import DigitalStepperMotor, CounterStepperMotor, SetPositionStoppedException, DisabledException
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

STEP_CHANNEL = 'step channel'
DELAY = 'delay'

STEP_OUTPUT_CHANNEL = 'step output channel'
STEP_INPUT_CHANNEL = 'step input channel'

ON_NEW_POSITION = 'on_new_position'
ON_BUSY_STATUS_CHANGED = 'on_busy_status_changed'
ON_ENABLED_STATUS_CHANGED = 'on_enabled_status_changed'

UPDATE_INTERVAL = .1

class StepperMotorBusyException(Exception): pass

class StepperMotorServer(LockServer):
    name = NAME    # Will be labrad name of server

    on_new_position = Signal(110,ON_NEW_POSITION,'(si)')
    on_busy_status_changed = Signal(111,ON_BUSY_STATUS_CHANGED,'(sb)')
    on_enabled_status_changed = Signal(112,ON_ENABLED_STATUS_CHANGED,'(sb)')

    @inlineCallbacks
    def initServer(self):  # Do initialization here
        reg = self.client.registry
        yield reg.cd(REGISTRY_PATH)
        stepper_motor_names = yield reg.dir()
        stepper_motor_names = stepper_motor_names[0] # just get directories
        self.stepper_motors = {name:None for name in stepper_motor_names}
        self.busy={name:False for name in stepper_motor_names}
        for stepper_motor in stepper_motor_names:
            yield self.update_stepper_motor(stepper_motor)
        yield LabradServer.initServer(self)

    @setting(17,stepper_motor_name='s',returns='b')
    def is_enableable(self,c,stepper_motor_name):
        return self.stepper_motors[stepper_motor_name].is_enableable()

    @setting(15,stepper_motor_name='s',returns='b')
    def is_enabled(self,c,stepper_motor_name):
        return self.stepper_motors[stepper_motor_name].is_enabled()

    @setting(16,stepper_motor_name='s',is_enabled='b')
    def set_enabled(self,c,stepper_motor_name,is_enabled):
        self.stepper_motors[stepper_motor_name].set_enabled(is_enabled)
        self.on_enabled_status_changed((stepper_motor_name,is_enabled))

    @setting(13,stepper_motor_name='s',returns='b')
    def is_busy(self,c,stepper_motor_name):
        return self.busy[stepper_motor_name]

    @setting(12,stepper_motor_name='s',returns='i')
    def get_position(self,c,stepper_motor_name):
        return self.stepper_motors[stepper_motor_name].get_position()

    def set_busy_status(self,stepper_motor_name,busy_status):
        self.busy[stepper_motor_name] = busy_status
        self.on_busy_status_changed((stepper_motor_name,busy_status))
        
    @lockable_setting(11,stepper_motor_name='s',position='i')
    def set_position(self,c,stepper_motor_name,position):
        print 'here sp'
        if self.busy[stepper_motor_name]:
            raise StepperMotorBusyException
        sm = self.stepper_motors[stepper_motor_name]
        old_position = sm.get_position()
        self.set_busy_status(stepper_motor_name,True)
        try:
            def update_position(_):
                if self.busy[stepper_motor_name]:
                    self.on_new_position(
                        (
                            stepper_motor_name,
                            old_position + {
                                sm.FORWARDS:1,
                                sm.BACKWARDS:-1
                            }[sm.get_direction()]*sm.get_pulses()
                        )
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
        self.set_busy_status(stepper_motor_name,False)
        reg = self.client.registry
        yield reg.cd(REGISTRY_PATH+[stepper_motor_name])
        yield reg.set(INIT_POS,int(new_position))
        self.on_new_position(
            (
                stepper_motor_name,
                new_position
            )
        )
        if failed:
            raise e

    @setting(14,stepper_motor_name='s')
    def stop(self,c,stepper_motor_name):
        self.stepper_motors[stepper_motor_name].stop()

    @inlineCallbacks
    def update_stepper_motor(self,stepper_motor):        
        reg = self.client.registry
        yield reg.cd(REGISTRY_PATH+[stepper_motor])
        
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
        self.stepper_motors[stepper_motor] = sm

    @setting(10, returns='*s')
    def get_stepper_motors(self,c):
        return self.stepper_motors.keys()

__server__ = StepperMotorServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
