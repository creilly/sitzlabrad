from daqmx import *
from daqmx.task import Task
class DOTask(Task):
    
    """

    Configures a channel for digital writing

    params:

        name: DAQmx indentifier for global digital output task.
            task must only contain a single line
    """
    def __init__(self,name):
        Task.__init__(self,name)
        channel = self.get_channels()[0]
        physical_channel = create_string_buffer(BUF_SIZE)
        daqmx(
            dll.DAQmxGetPhysicalChanName,
            (
                self.handle, 
                channel, 
                physical_channel, 
                BUF_SIZE
                )
            )
        self.exponent = int(
            physical_channel.value.split('/')[-1].split('line')[-1]
            )
    """

    Sets the state of the digital line

    params:

        state: state to write

    """
    def write_state( self, state ):
        daqmx(
            dll.DAQmxWriteDigitalScalarU32,
            (
                self.handle,
                True,
                c_double(TIMEOUT),
                int(state) * 2 ** self.exponent,
                None
            )
        )

if __name__ == '__main__':    
    tasks = Task.get_global_tasks()
    print '\n'.join(
        '%d:\t%s' % ( index, name )
        for index, name in enumerate(tasks)
        )
    do_task = DOTask(tasks[int(raw_input('--> '))])
    print 'writing true'
    do_task.write_state(True)
    print 'write false'
    do_task.write_state(False)
