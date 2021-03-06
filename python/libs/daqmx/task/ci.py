from daqmx import *
from daqmx.task import Task
from ctypes import *

class CITask(Task):
    def __init__(self,name):
        Task.__init__(self,name)
        self.count = 0
        
    def start_counting(self):
        daqmx(
            dll.DAQmxStartTask,
            (
                self.handle,
            )
        )

    def stop_counting(self):
        self.count = self._get_count()
        daqmx(
            dll.DAQmxStopTask,
            (
                self.handle,
            )
        )

    def _get_count(self):
        count = c_uint32(0)
        daqmx(
            dll.DAQmxReadCounterScalarU32,
            (
                self.handle, 
                c_double(constants['DAQmx_Val_WaitInfinitely']), 
                byref(count),
                None
            )
        )
        return count.value        

    def get_count(self):
        if self.is_done():
            return self.count        
        else:
            return self._get_count()
