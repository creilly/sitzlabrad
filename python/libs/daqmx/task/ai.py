from daqmx import *
from daqmx.task import Task
import numpy as np
from time import clock
class AITask(Task):
    RISING, FALLING = 'rising','falling'

    def __init__(self,*channels):
        Task.__init__(self,*channels)
        daqmx(
            dll.DAQmxSetSampQuantSampMode,
            (
                self.handle,
                constants['DAQmx_Val_FiniteSamps']
            )
        )
        daqmx(
            dll.DAQmxSetSampTimingType,
            (
                self.handle,
                constants['DAQmx_Val_SampClk']
            )
        )

    def acquire_samples(self):
        daqmx(
            dll.DAQmxStartTask,
            (
                self.handle,
            )
        )
        daqmx(
            dll.DAQmxWaitUntilTaskDone,
            (
                self.handle,                
                c_double(constants['DAQmx_Val_WaitInfinitely'])
            )
        )        
        bufSize = c_uint32(0)
        daqmx(
            dll.DAQmxGetBufInputBufSize,
            (
                self.handle,
                byref(bufSize)
            )
        )
        channels = self.get_channels()
        bufSize = bufSize.value * len(self.get_channels())        
        samples = np.zeros(bufSize)
        samplesRead = c_int(0)
        daqmx(
            dll.DAQmxReadAnalogF64,
            (
                self.handle,
                constants['DAQmx_Val_Auto'],
                c_double(TIMEOUT), 
                constants['DAQmx_Val_GroupByChannel'],
                samples.ctypes.data_as(POINTER(c_double)), 
                bufSize,                
                byref(samplesRead), 
                None
            )
        )

        samplesRead = samplesRead.value
        byChannel = np.reshape(
            samples[:len(channels) * samplesRead],
            (len(channels),samplesRead)
            )
        daqmx(
            dll.DAQmxStopTask,
            (
                self.handle,
            )
        )
        return {channel: data for channel, data in zip(channels,byChannel)}

    def get_sampling_rate(self):
        sampling_rate = c_double(0)
        daqmx(
            dll.DAQmxGetSampClkRate,
            (
                self.handle,
                byref(sampling_rate)
            )
        )
        return sampling_rate.value
    
    def set_sampling_rate(self,sampling_rate):
        daqmx(
            dll.DAQmxSetSampClkRate,
            (
                self.handle,
                c_double(sampling_rate)
            )
        )
        
    def get_max_sampling_rate(self):
        max_sampling_rate = c_double(0.)
        daqmx(
            dll.DAQmxGetSampClkMaxRate,
            (
                self.handle,
                byref(max_sampling_rate)
            )
        )
        return max_sampling_rate.value
    
    def set_sample_quantity(self,sample_quantity):
        daqmx(
            dll.DAQmxSetSampQuantSampPerChan,
            (
                self.handle,
                c_uint64(sample_quantity) # !!!
            )
        )
        
    def get_sample_quantity(self):
        sample_quantity = c_uint64(0)
        daqmx(
            dll.DAQmxGetSampQuantSampPerChan,
            (
                self.handle,
                byref(sample_quantity)
            )
        )
        return sample_quantity.value
        
    def set_trigger(self,source,edge):
        daqmx(
            dll.DAQmxCfgDigEdgeStartTrig,
            (
                self.handle,
                source,
                {
                    self.RISING:constants['DAQmx_Val_Rising'],
                    self.FALLING:constants['DAQmx_Val_Falling']
                }[edge]
            )
        )
    def unset_trigger(self):
        daqmx(
            dll.DAQmxDisableStartTrig,
            (
                self.handle,
            )
        )
    def is_triggering(self):
        trigger_type = c_int32(0)
        daqmx(
            dll.DAQmxGetStartTrigType,
            (
                self.handle,
                byref(trigger_type)
            )
        )
        return trigger_type.value == constants['DAQmx_Val_DigEdge']

    def get_trigger_source(self):
        source = create_string_buffer(BUF_SIZE)
        daqmx(
            dll.DAQmxGetDigEdgeStartTrigSrc,
            (
                self.handle,
                source,
                BUF_SIZE
            )
        )
        return source.value

    def get_trigger_edge(self):
        edge = c_int32(0)
        daqmx(
            dll.DAQmxGetDigEdgeStartTrigEdge,
            (
                self.handle,
                byref(edge)
            )
        )
        return {
            constants['DAQmx_Val_Rising']:self.RISING,
            constants['DAQmx_Val_Falling']:self.FALLING
        }[edge.value]
