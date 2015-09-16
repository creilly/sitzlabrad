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
    def write_voltage( self, voltage ):
        daqmx(
            dll.DAQmxWriteAnalogScalarF64,
            (
                self.handle,
                True,
                c_double(TIMEOUT),
                c_double(voltage),
                None
            )
        )

