from labrad.wrappers import connectAsync
from twisted.internet.defer import Deferred, inlineCallbacks, returnValue
from twisted.internet import reactor
import numpy as np
from scandefs import *
from voltmeterclient import VoltmeterClient
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
        self._on_start_d = self.on_start()

    def on_start(self):
        pass

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
        if self._on_start_d is not None:
            yield self._on_start_d
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
        raise NotImplementedError('_get_input')
    def set_input(self):
        raise NotImplementedError('set_input')

class StepperMotorInput(ScanInput,LabradScanItem):
    OVERSHOOT = 500
    def __init__(self,sm_name,scan_range):
        self.sm_name = sm_name
        self.sm_server = None
        LabradScanItem.__init__(self)
        ScanInput.__init__(self,scan_range)

    @inlineCallbacks
    def on_start(self):
        sm = yield self.get_stepper_motor_server()
        is_enableable = yield sm.is_enableable()
        if is_enableable:
            yield sm.set_enabled(True)
        
    @inlineCallbacks
    def get_stepper_motor_server(self):
        if self.sm_server is None:
            client = yield self.get_client()
            sm = client.stepper_motor
            yield sm.select_device(self.sm_name)
            self.sm_server = sm
        returnValue(self.sm_server)

    @inlineCallbacks
    def _get_input(self):
        sm_server = yield self.get_stepper_motor_server()
        input = yield sm_server.get_position()
        returnValue(input)

    @inlineCallbacks
    def set_input(self,input):
        sm_server = yield self.get_stepper_motor_server()
        old_position = yield self.sm_server.get_position()
        if old_position > input:
            yield sm_server.set_position(
                input-{
                    'lid':3000,
                    'kdp':500,
                    'bbo':500,
                    'probe vertical':10000,
                    'pol':20,
                    'pdl':75                    
                }.get(self.sm_name,self.OVERSHOOT)
            )
        yield sm_server.set_position(input)

class DelayGeneratorInput(ScanInput,LabradScanItem):
    def __init__(self,dg_name,scan_range):
        self.dg_name = dg_name
        self.dg_server = None
        LabradScanItem.__init__(self)
        ScanInput.__init__(self,scan_range)
        
    @inlineCallbacks
    def get_delay_generator_server(self):
        if self.dg_server is None:
            client = yield self.get_client()
            dg_server = client.delay_generator
            yield dg_server.select_device(self.dg_name)
            self.dg_server = dg_server
        returnValue(self.dg_server)

    @inlineCallbacks
    def _get_input(self):
        dg_server = yield self.get_delay_generator_server()
        input = yield dg_server.get_delay()
        returnValue(input)

    @inlineCallbacks
    def set_input(self,input):
        dg_server = yield self.get_delay_generator_server()
        yield dg_server.set_delay(input)

class DelayGeneratorChainInput(ScanInput,LabradScanItem):
    def __init__(self,master,slaves,scan_range):
        self.master = master
        self.slaves = slaves
        self.dg_server = None
        LabradScanItem.__init__(self)
        ScanInput.__init__(self,scan_range)

    @inlineCallbacks
    def get_delay_generator_server(self):
        if self.dg_server is None:
            client = yield self.get_client()
            dg = client.delay_generator
            self.dg_server = dg
            yield dg.select_device(self.master)
            master_delay = yield dg.get_delay()
            self.deltas = {}
            for slave in self.slaves:
                yield dg.select_device(slave)
                slave_delay = yield dg.get_delay()
                self.deltas[slave] = slave_delay - master_delay
        returnValue(self.dg_server)
        
    @inlineCallbacks
    def _get_input(self):
        dg = yield self.get_delay_generator_server()
        yield dg.select_device(self.master)
        delay = yield dg.get_delay()
        returnValue(delay)

    @inlineCallbacks
    def set_input(self,input):
        dg = yield self.get_delay_generator_server()
        yield dg.select_device(self.master)
        yield dg.set_delay(input)
        for slave in self.slaves:
            yield dg.select_device(slave)
            yield dg.set_delay(input+self.deltas[slave])

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
        self.channel_initialized = False

    @inlineCallbacks
    def get_voltmeter_client(self):
        client = yield self.get_client()
        if not self.channel_initialized:
            active_channels = yield client.voltmeter.get_active_channels()
            if self.channel not in active_channels:
                yield client.voltmeter.set_active_channels(active_channels + [self.channel])
            self.channel_initialized = True
        returnValue(VoltmeterClient(client.voltmeter,self.channel))

    @inlineCallbacks
    def get_output(self):
        vmc = yield self.get_voltmeter_client()
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
    def get_voltmeter_client(self,channel):
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
            vmc = yield self.get_voltmeter_client(entry)
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

# measures peak height
class AugerOutput(LabradScanItem):
    INPUT_CHANNEL = 'auger input'
    OUTPUT_CHANNEL = 'auger output'
    UPDATE_RATE = 30. # response time of hv supply in ev/s
    def __init__(self,bottom_energy,top_energy,duration):
        LabradScanItem.__init__(self)
        self.bottom_energy = bottom_energy
        self.top_energy = top_energy
        self.initialized = self.initialize(duration)
        
    @inlineCallbacks
    def initialize(self,duration):
        client = yield self.get_client()
        yield client.analog_output.select_device(self.OUTPUT_CHANNEL)
        yield client.voltmeter.set_active_channels([self.INPUT_CHANNEL])
        yield client.voltmeter.set_sampling_duration(duration)

    @inlineCallbacks
    def get_output(self):
        yield self.initialized
        yield self.set_energy(self.bottom_energy)
        bottom_signal = yield self.get_signal()
        yield self.set_energy(self.top_energy)
        top_signal = yield self.get_signal()
        returnValue(top_signal-bottom_signal)

    @inlineCallbacks
    def get_signal(self):
        client = yield self.get_client()
        signal = yield client.voltmeter.get_sample(self.INPUT_CHANNEL)
        returnValue(signal)

    @inlineCallbacks
    def set_energy(self,energy):
        client = yield self.get_client()
        previous_energy = yield client.analog_output.get_value()
        delta_energy = abs(energy-previous_energy)
        client.analog_output.set_value(energy)
        d = Deferred()
        reactor.callLater(
            delta_energy / self.UPDATE_RATE,
            d.callback,
            None
        )
        yield d

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
