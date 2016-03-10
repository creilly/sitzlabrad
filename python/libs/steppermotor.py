from daqmx.task.co import GenerationStoppedException
from time import sleep

class NotEnableableException(Exception):
    args = ['stepper motor is not enableable']
class SetPositionStoppedException(Exception):
    args = ['set position operation stopped']
class DisabledException(Exception):
    args = ['can not set position when stepper motor is disabled']

class StepperMotor:
    FORWARDS = True
    BACKWARDS = False

    ENABLED = True
    DISABLED = False
    def __init__( 
        self,
        dir_task,
        enable_task = None,            
        init_pos = 0, 
        init_enabled = False,
        enable_level = True,
        forwards_level = True
        ):
        self.enable_task = enable_task
        self.enable_level = enable_level
        if enable_task is not None:
            self.set_enabled(init_enabled)
        self.direction_task = dir_task
        self.position = init_pos
        self.direction = None
        self.forwards_level = forwards_level

    # oh god is that even a word?
    def is_enableable(self):
        return self.enable_task is not None

    def set_enabled(self,is_enabled):
        if not self.is_enableable():
            raise NotEnableableException
        self.enable_task.write_state(
            {
                self.ENABLED:self.enable_level,
                self.DISABLED:not self.enable_level
            }[is_enabled]
        )
        self._is_enabled = is_enabled

    def is_enabled(self):
        return self._is_enabled if self.is_enableable() else self.ENABLED

    def set_direction(self,direction):
        if direction is self.get_direction():
            return
        self.direction = direction
        self.direction_task.write_state(
            {
                self.FORWARDS:self.forwards_level,
                self.BACKWARDS:not self.forwards_level
            }[direction]
        )

    def get_direction(self):
        return self.direction

    def set_position(self,position):
        if not self.is_enabled():
            raise DisabledException
        old_position = self.get_position()
        delta = position - old_position
        if delta is 0: return
        self.set_direction(delta > 0)
        pulses = self.generate_pulses(abs(delta))
        self.position = old_position + (
            1 if delta > 0 else -1 
        ) * pulses
        if pulses != abs(delta):
            raise SetPositionStoppedException

    def get_position(self):
        return self.position
    
    def generate_pulses(self,pulses):
        raise NotImplementedError

    def get_pulses(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError        

class DigitalStepperMotor(StepperMotor):
    def __init__( 
        self,
        step_task,
        delay,
        dir_task, 
        enable_task = None,
        init_pos = 0, 
        init_enable = False,
        enable_level = True,
        forwards_level = True
        ):
        StepperMotor.__init__(
            self,
            dir_task, 
            enable_task,
            init_pos, 
            init_enable,
            enable_level,
            forwards_level
        )
        self.step_task = step_task
        self.delay = delay
        self.stopped = False
        self.pulses = 0                

    def generate_pulses(self,pulses):
        self.stopped = False
        self.pulses = 0
        for pulse in range(pulses):
            if self.stopped:
                self.stopped = False
                break
            self.step_task.write_state(True)
            sleep(self.delay / 2.)
            self.step_task.write_state(False)
            sleep(self.delay / 2.)
            self.pulses += 1
        return self.pulses

    def get_pulses(self):
        return self.pulses

    def stop(self):
        self.stopped = True

class CounterStepperMotor(StepperMotor):
    def __init__( 
        self,
        step_output_task,
        step_input_task,
        dir_task, 
        enable_task = None,
        init_pos = 0, 
        init_enable = False,
        enable_level = True,
        forwards_level = True
        ):
        StepperMotor.__init__(
            self,
            dir_task,
            enable_task,
            init_pos,
            init_enable,
            enable_level,
            forwards_level
        )
        self.step_output_task = step_output_task
        self.step_input_task = step_input_task

    def generate_pulses(self,pulses):
        self.step_input_task.start_counting()
        try:
            self.step_output_task.generate_pulses(pulses)
        except GenerationStoppedException:
            pass
        generated = self.step_input_task.get_count()
        self.step_input_task.stop_counting()
        return generated

    def stop(self):
        self.step_output_task.stop_generation()

    def get_pulses(self):
        return self.step_input_task.get_count()
