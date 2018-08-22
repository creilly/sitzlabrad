from serialtransceiver import HandshakeSerialDevice
from daqmx.task.co import GenerationStoppedException
from threading import Lock
from time import sleep
import socket

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
        dir_manager,
        enable_manager = None,            
        init_pos = 0, 
        init_enabled = DISABLED
        ):
        self._is_busy = False
        self.enable_manager = enable_manager
        self._is_enabled = None
        if enable_manager is not None:
            self.set_enabled(init_enabled)
            self._is_enabled = init_enabled
        else:
            self._is_enabled = self.ENABLED
        self.dir_manager = dir_manager
        self.position = init_pos
        self.direction = None

    # oh god is that even a word?
    def is_enableable(self):
        return self.enable_manager is not None

    def set_enabled(self,is_enabled):
        if not self.is_enableable():
            raise NotEnableableException
        if is_enabled is not self.is_enabled():            
            self.enable_manager.set_enabled(is_enabled)
            self._is_enabled = is_enabled

    def is_enabled(self):
        return self._is_enabled

    def set_direction(self,direction):
        if direction is not self.get_direction():            
            self.dir_manager.set_direction(direction)
            self.direction = direction

    def get_direction(self):
        return self.direction

    def set_position(self,position):
        if not self.is_enabled():
            raise DisabledException
        old_position = self.get_position()
        delta = position - old_position
        if delta is 0: return
        self.set_direction(
            self.FORWARDS if delta > 0 else self.BACKWARDS
        )
        self._is_busy = True
        pulses = self.generate_pulses(abs(delta))
        self._is_busy = False
        self.position = old_position + (
            1 if delta > 0 else -1
        ) * pulses
        if pulses != abs(delta):
            raise SetPositionStoppedException

    def get_position(self):
        return self.position + (
            0 if not self.is_busy() else {
                self.FORWARDS:+1,
                self.BACKWARDS:-1
            }[self.get_direction()] * self.get_pulses()
        )
    
    def generate_pulses(self,pulses):
        raise NotImplementedError

    def get_pulses(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def is_busy(self):
        return self._is_busy

class DigitalEnableManager:
    def __init__(self,task,enable_level=True):
        self.task = task
        self.enable_level = enable_level
        
    def set_enabled(self,is_enabled):
        self.task.write_state(
            {
                StepperMotor.ENABLED:self.enable_level,
                StepperMotor.DISABLED:not self.enable_level
            }[is_enabled]
        )

class DigitalDirectionManager:
    def __init__(self,task,forwards_level=True):
        self.task = task
        self.forwards_level = forwards_level

    def set_direction(self,direction):
        self.task.write_state(
            {
                StepperMotor.FORWARDS:self.forwards_level,
                StepperMotor.BACKWARDS:not self.forwards_level
            }[direction]
        )

class DigitalDirEnableStepperMotor(StepperMotor):
    def __init__(
        self,
        dir_task,
        enable_task = None,
        init_pos = 0, 
        init_enable = StepperMotor.DISABLED,
        enable_level = True,
        forwards_level = True
        ):
        StepperMotor.__init__(
            self,
            DigitalDirectionManager(dir_task,forwards_level), 
            DigitalEnableManager(enable_task,enable_level) if enable_task is not None else None,
            init_pos,
            init_enable,
        )

class DigitalStepperMotor(DigitalDirEnableStepperMotor):
    def __init__(
        self,
        step_task,
        delay,
        dir_task,
        enable_task = None,
        init_pos = 0, 
        init_enable = StepperMotor.DISABLED,
        enable_level = True,
        forwards_level = True
        ):
        DigitalDirEnableStepperMotor.__init__(self,dir_task,enable_task,init_pos,init_enable,enable_level,forwards_level)
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

class CounterStepperMotor(DigitalDirEnableStepperMotor):
    def __init__( 
        self,
        step_output_task,
        step_input_task,
        dir_task, 
        enable_task = None,
        init_pos = 0, 
        init_enable = StepperMotor.DISABLED,
        enable_level = True,
        forwards_level = True
        ):
        DigitalDirEnableStepperMotor.__init__(self,dir_task,enable_task,init_pos,init_enable,enable_level,forwards_level)
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

from serialtransceiver import HandshakeSerialDevice

BAUDRATE = 115200
TIMEOUT = None

RSM_HANDSHAKE_RESPONSE = 'H'
ID_COMMAND = 'i'

class RampStepperMotor(DigitalDirEnableStepperMotor):
    def __init__( 
        self,
        rsm_id,
        stop_task,
        step_task,
        dir_task, 
        enable_task = None,
        init_pos = 0, 
        init_enable = StepperMotor.DISABLED,
        enable_level = True,
        forwards_level = True
        ):
        DigitalDirEnableStepperMotor.__init__(self,dir_task,enable_task,init_pos,init_enable,enable_level,forwards_level)
        self.rsm = HandshakeSerialDevice(
            RSM_HANDSHAKE_RESPONSE,
            ID_COMMAND,
            rsm_id,
            BAUDRATE,
            TIMEOUT
        )
        self.stop_task = stop_task
        self.step_task = step_task

    def generate_pulses(self,pulses):        
        self.step_task.start_counting()
        self.rsm.write_line('g')
        self.rsm.read_line() # serial device replies with 'g'
        self.rsm.write_line(str(pulses))
        self.rsm.read_line() # replies with response code, steps generated, and some junk
        generated = self.step_task.get_count()
        self.step_task.stop_counting()
        return generated

    def stop(self):
        # stop interrupt looks for rising edge
        self.stop_task.write_state(False) 
        self.stop_task.write_state(True)

    def get_pulses(self):        
        return self.step_task.get_count()

class NetworkDevice:
    BUF_SIZE = 1024    
    def __init__(self,ip,port):
        self.address = (ip,port)

    def send_message(self,message):
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection.connect(self.address)
        connection.send(message + '\n')
        return connection.recv(self.BUF_SIZE)        

class NetworkDirectionManager(NetworkDevice):
    def __init__(self,ip,port):
        NetworkDevice.__init__(self,ip,port)
        
    def set_direction(self,direction):
        self.send_message('d %d' % {StepperMotor.FORWARDS:1,StepperMotor.BACKWARDS:0}[direction])

class NetworkStepperMotor(StepperMotor,NetworkDevice):
    def __init__(self,ip,port):
        StepperMotor.__init__(self,NetworkDirectionManager(ip,port),None,init_pos=0,init_enabled=StepperMotor.DISABLED)
        NetworkDevice.__init__(self,ip,port)

    def generate_pulses(self,pulses):
        return int(self.send_message('s %d' % pulses))

    def stop(self):
        self.send_message('p')

    def get_pulses(self):
        return int(self.send_message('g'))

SSM_HANDSHAKE_RESPONSE = 'r'
SET_DIRECTION = 'd'
GENERATE_PULSES = 's'
GET_PULSES = 'g'
STOP = 'p'
FINISHED = 'f'

class SerialStepperMotor(StepperMotor):
    def __init__(self,sm_id):
        self.lock = Lock()
        self.dev = HandshakeSerialDevice(
            SSM_HANDSHAKE_RESPONSE,
            ID_COMMAND,
            sm_id,
            BAUDRATE,
            TIMEOUT
        )

        class DirectionManager:
            def __init__(self,sm):
                self.sm = sm

            def set_direction(self,direction):
                self.sm.send_message('%s %d' % (SET_DIRECTION,direction))

        StepperMotor.__init__(
            self,
            DirectionManager(self)
        )

    def generate_pulses(self,pulses):
        response = int(self.send_message('%s %d' % (GENERATE_PULSES,pulses)))
        while response < 0: # pulse count exceded threshold
            sleep(.1)
            response = int(self.send_message(FINISHED))
        return response

    def stop(self):
        self.send_message(STOP)

    def get_pulses(self):
        return int(self.send_message(GET_PULSES))

    def send_message(self,message):
        self.lock.acquire()
        self.dev.write_line(message)
        response = self.dev.read_line().strip()
        self.lock.release()
        return response
