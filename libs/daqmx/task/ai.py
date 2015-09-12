from daqmx import *
from daqmx.task import Task

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
        samples = numpy.zeros(bufSize)
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
        byChannel = numpy.reshape(
            samples[:len(channels) * samplesRead],
            (len(channels),samplesRead)
            )
        return {channel: data for channel, data in zip(channels,byChannel)}

if __name__ == '__main__':
    import numpy as np
    tasks = Task.get_global_tasks()
    print '\n'.join(
        '%d:\t%s' % ( index, name )
        for index, name in enumerate(tasks)
        )
    ai_task = AITask(tasks[int(raw_input('--> '))])
    print 'acquiring...'
    samples = ai_task.acquire_samples()
    for channel, series in samples.items():
        print 'channel', channel, \
            'mean', np.average(series), \
            'std', np.std(series)
        
