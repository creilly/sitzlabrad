from time import sleep
class StepperMotor:
    FORWARDS = True
    BACKWARDS = False
    def __init__( 
        self,
        step_task, 
        dir_task, 
        init_pos = 0, 
        init_dir = FORWARDS, 
        backlash = 0, 
        delay = 0.,
        enable_task = None
        ):
        self.step_task = step_task
        self.direction_task = dir_task
        self.enable_task = enable_task
        self.position = init_pos
        self.backlash = backlash
        self.direction = None
        self.delay = delay
        self.set_direction(init_dir)

    def set_direction(self,direction):        
        if direction is self.get_direction():
            return
        self.direction = direction
        self.direction_task.write_state(direction)        

    def get_direction(self):
        return self.direction

    def set_position(self,position):
        delta = position - self.get_position()
        needs_enabling = self.enable_task is not None
        if needs_enabling:
            self.enable_task.write_state(True)
        if delta is 0: return     
        if (delta > 0) is not self.direction:            
            self.set_direction( not self.get_direction() )
            for _ in range(self.backlash+abs(delta)):
                self.step()
        else:
            for _ in range(abs(delta)):
                self.step()
        if needs_enabling:
            self.enable_task.write_state(False)
        self.position = position

    def get_position(self):
        return self.position
                
    def step(self):
        self.step_task.write_state(True)
        sleep(self.delay / 2.)
        self.step_task.write_state(False)
        sleep(self.delay / 2.)
