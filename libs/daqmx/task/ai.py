from daqmx import *
from daqmx.task import Task
import numpy as np

class AITask(Task):
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
        daqmx(
            dll.DAQmxStopTask,
            (
                self.handle,
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
        bufSize = bufSize.value        
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
        channels = self.get_channels()
        byChannel = np.reshape(
            samples[:len(channels) * samplesRead],
            (len(channels),samplesRead)
            )
        return {channel: data for channel, data in zip(channels,byChannel)}

