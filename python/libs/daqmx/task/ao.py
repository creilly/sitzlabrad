from daqmx import *
from daqmx.task import Task

"""

Only works for one channel

"""
class AOTask(Task):
    
    """

    params:

        voltage: new voltage to set

    """
    def write_sample( self, sample ):
        daqmx(
            dll.DAQmxWriteAnalogScalarF64,
            (
                self.handle,
                True,
                c_double(TIMEOUT),
                c_double(sample),
                None
            )
        )

    def get_min(self):
        min_value = c_double(0)
        daqmx(
            dll.DAQmxGetAOMin,
            (
                self.handle,
                self.get_channels()[0],
                byref(min_value)
            )
        )
        return min_value.value

    def get_max(self):
        max_value = c_double(0)
        daqmx(
            dll.DAQmxGetAOMax,
            (
                self.handle,
                self.get_channels()[0],
                byref(max_value)
            )
        )
        return max_value.value
    
    def get_units(self):
        return Task.get_units(self).values()[0]
    
