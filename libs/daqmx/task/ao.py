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

if __name__ == '__main__':
    tasks = Task.get_global_tasks()
    print '\n'.join(
        '%d:\t%s' % ( index, name )
        for index, name in enumerate(tasks)
        )
    ao_task = AOTask(tasks[int(raw_input('--> '))])
    print 'writing 4.5'
    ao_task.write_voltage(4.5)

