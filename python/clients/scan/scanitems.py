from labrad.wrappers import connectAsync
from twisted.internet.defer import Deferred, inlineCallbacks, returnValue
from twisted.internet import reactor
import numpy as np
from scandefs import *
from steppermotorclient import StepperMotorClient
from voltmeterclient import VoltmeterClient
from delaygeneratorclient import DelayGeneratorClient
from operator import add, sub, mul, div

np.random.seed()

COUNT = 100

class LabradScanItem:
    def __init__(self):
        self._d = connectAsync()
        self._client_connecting = False

    @inlineCallbacks
    def get_client(self):
        if self._d is not None:
            if not self._client_connecting:
                self._client_connecting = True
                self._client_connecting_d = Deferred()
                self._client = yield self._d
                self._d = None
                self._client_connecting_d.callback(None)
            else:
                yield self._client_connecting_d            
        returnValue(self._client)
        
# inheritors must implement self._get_input and self.set_input
class ScanInput:
    def __init__(self,scan_range):
        self.scan_range = scan_range
        self._scan_range_d = self.init_range()

    @inlineCallbacks
    def init_range(self):
        sr = self.scan_range
        scan_class = sr.get(CLASS,RANGE)
        if scan_class == RANGE:
            start = sr[START]
            stop = sr[STOP]
            step = sr[STEP]
            if sr.get(RELATIVE,False):
                delta = stop - start
                current_input = yield self._get_input()
                start = current_input - delta / 2
                stop = current_input + delta / 2
            self.scan_list = list(
                np.arange(start,stop,step)
            )
        
    @inlineCallbacks
    def get_input(self):
        if self._scan_range_d is not None:
            yield self._scan_range_d
            self._scan_range_d = None
        sr = self.scan_range
        scan_class = sr[CLASS]
        if scan_class == RANGE:
            if self.scan_list:
                input = self.scan_list.pop(0)
                yield self.set_input(input)
                returnValue(input)
            else:
                returnValue(None)

    def _get_input(self):
        return None

class StepperMotorInput(ScanInput,LabradScanItem):
    OVERSHOOT = 500
    def __init__(self,sm_name,scan_range):
        LabradScanItem.__init__(self)
        ScanInput.__init__(self,scan_range)
        self.sm_name = sm_name
        
    @inlineCallbacks
    def get_stepper_motor_client(self):
        client = yield self.get_client()
        returnValue(StepperMotorClient(self.sm_name,client.stepper_motor))

    @inlineCallbacks
    def _get_input(self):
        smc = yield self.get_stepper_motor_client()
        input = yield smc.get_position()
        returnValue(input)

    @inlineCallbacks
    def set_input(self,input):
        smc = yield self.get_stepper_motor_client()
        old_position = yield self._get_input()
        if old_position > input:
            yield smc.set_position(input-self.OVERSHOOT)
        yield smc.set_position(input)

class DelayGeneratorInput(ScanInput,LabradScanItem):
    def __init__(self,dg_id,scan_range):
        LabradScanItem.__init__(self)
        ScanInput.__init__(self,scan_range)
        self.dg_id = dg_id
        
    @inlineCallbacks
    def get_delay_generator_client(self):
        client = yield self.get_client()
        returnValue(DelayGeneratorClient(self.dg_id,client.delay_generator))

    @inlineCallbacks
    def _get_input(self):
        dgc = yield self.get_delay_generator_client()
        input = yield dgc.get_delay()
        returnValue(input)

    @inlineCallbacks
    def set_input(self,input):
        dgc = yield self.get_delay_generator_client()
        yield dgc.set_delay(input)

class TestScanInput(ScanInput):
    def _get_input(self):
        return np.random.randint(COUNT)
    def set_input(self,input):
        d = Deferred()
        reactor.callLater(.1,d.callback,None)
        return d

class VoltmeterOutput(LabradScanItem):
    def __init__(self,channel,shots):
        LabradScanItem.__init__(self)
        self.channel = channel
        self.shots = shots

    @inlineCallbacks
    def get_volt_meter_client(self):
        client = yield self.get_client()
        returnValue(VoltmeterClient(client.voltmeter,self.channel))

    @inlineCallbacks
    def get_output(self):
        vmc = yield self.get_volt_meter_client()
        output = yield vmc.get_average(self.shots)
        returnValue(output)

class VoltmeterMathOutput(LabradScanItem):
    ADD, SUBTRACT, MULTIPLY, DIVIDE = '+','-','*','/'
    operations = {
        ADD:add,
        SUBTRACT:sub,
        MULTIPLY:mul,
        DIVIDE:div
    }
    def __init__(self,formula,shots):
        LabradScanItem.__init__(self)
        self.formula = formula
        self.shots = shots

    @inlineCallbacks
    def get_volt_meter_client(self,channel):
        client = yield self.get_client()
        returnValue(VoltmeterClient(client.voltmeter,channel))

    # reverse polish notation evaluator
    @inlineCallbacks
    def get_output(self):
        deferreds = {}
        for entry in self.formula:
            if type(entry) is not str:
                continue
            if entry in self.operations:
                continue
            if entry in deferreds:
                continue
            vmc = yield self.get_volt_meter_client(entry)
            deferreds[entry] = vmc.get_average(self.shots)
        voltages = {}
        for channel, deferred in deferreds.items():
            voltage = yield deferred
            voltages[channel] = voltage
        stack = []
        for entry in self.formula:
            if entry in self.operations:
                v1 = stack.pop()
                v2 = stack.pop()
                stack.append(self.operations[entry](v2,v1))
            else:
                if type(entry) is str:
                    stack.append(voltages[entry])
                else:
                    stack.append(entry)
        returnValue(stack.pop())

class TestOutput:
    def __init__(self):
        self.index = 0
        self.mean = np.random.randint(COUNT)
        self.std = 1. * np.random.randint(COUNT) / 2 + 1.
        self.amplitude = np.random.randint(COUNT)
        self.offset = np.random.randint(COUNT)

    def get_output(self):
        d = Deferred()
        reactor.callLater(
            .1,
            d.callback,
            self.amplitude * ( 
                np.random.rand() / 5 + np.exp(
                    -1. / 2. * np.square( 
                        1. * ( self.index - self.mean ) / self.std
                    )
                )
            ) + self.offset
        )
        self.index += 1
        return d
