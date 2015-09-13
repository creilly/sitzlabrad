from labrad.server import LabradServer, setting, Signal
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
import labrad
from steppermotor import StepperMotor
from daqmx.task.do import DOTask
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
STEP_TASK_NAME = 'step task name'
DIR_TASK_NAME = 'direction task name'
INIT_POS = 'initial position'
BACKLASH = 'backlash'
INIT_DIR = 'initial direction' # true:forwards, false:backwards
DELAY = 'delay'

ON_NEW_POSITION = 'on_new_position'

class StepperMotorServer(LabradServer):
    name = NAME    # Will be labrad name of server

    on_new_position = Signal(110,ON_NEW_POSITION,'(si)')

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

    @setting(12,stepper_motor_name='s',returns='i')
    def get_position(self,c,stepper_motor_name):
        return self.stepper_motors[stepper_motor_name].get_position()

    @inlineCallbacks
    @setting(11,stepper_motor_name='s',position='i')
    def set_position(self,c,stepper_motor_name,position):
        sm = self.stepper_motors[stepper_motor_name]
        yield deferToThread(
            sm.set_position,
            position
            )
        reg = self.client.registry
        yield reg.cd(REGISTRY_PATH+[stepper_motor_name])
        yield reg.set(INIT_POS,sm.get_position())
        yield reg.set(INIT_DIR,sm.get_direction())
        self.on_new_position((stepper_motor_name,position))

    @inlineCallbacks
    def update_stepper_motor(self,stepper_motor):        
        reg = self.client.registry
        yield reg.cd(REGISTRY_PATH+[stepper_motor])
        step_task_name = yield reg.get(STEP_TASK_NAME)
        dir_task_name = yield reg.get(DIR_TASK_NAME)
        init_pos = yield reg.get(INIT_POS)
        backlash = yield reg.get(BACKLASH)
        init_dir = yield reg.get(INIT_DIR)
        delay = yield reg.get(DELAY)
        self.stepper_motors[stepper_motor] = StepperMotor(
            DOTask(step_task_name),
            DOTask(dir_task_name),
            init_pos,
            backlash,
            init_dir,
            delay
            )

    @setting(10, returns='*s')
    def get_stepper_motors(self,c):
        return self.stepper_motors.keys()

__server__ = StepperMotorServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
