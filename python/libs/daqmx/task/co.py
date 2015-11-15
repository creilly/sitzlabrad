from daqmx import *
from daqmx.task import Task
from ctypes import *

class GenerationStoppedException(Exception):
    def __init__(self):
        Exception.__init__(self,'pulse generation stopped')

class COTask(Task):
    def __init__(self,name):
        Task.__init__(self,name)
        self.stopped = False
    """

    generates a specified number of pulses. raises DAQmxException if generated stopped early

    params:

        state: state to write

    """
    def generate_pulses(self, count):
        self.stopped = False
        daqmx(
            dll.DAQmxSetSampQuantSampPerChan,
            (
                self.handle,
                c_uint64(count)
            )
        )
        daqmx(
            dll.DAQmxStartTask,
            (
                self.handle,
            )
        )
        while True:            
            if self.is_done():                
                daqmx(
                    dll.DAQmxStopTask,
                    (
                        self.handle,
                    )
                )
                break
            if self.stopped:
                self.stopped = False
                try:
                    daqmx(
                        dll.DAQmxStopTask,
                        (
                            self.handle,
                        )
                    )
                except DAQmxException, e:
                    if e.code != 200010:
                        raise
                raise GenerationStoppedException()
            
    def stop_generation(self):
        self.stopped = True

if __name__ == '__main__':
    from twisted.internet import reactor
    from twisted.internet.threads import deferToThread
    from twisted.internet.defer import Deferred, inlineCallbacks, returnValue
    @inlineCallbacks
    def main():
        co = COTask('lid step output task')
        def stop_on_enter():
            raw_input('press enter to stop')
            co.stop_generation()
            print 'stopped'
        gen_thread = deferToThread(co.generate_pulses,200)
        input_thread = deferToThread(stop_on_enter)
        yield gen_thread
        yield input_thread
        reactor.stop()
    reactor.callWhenRunning(main)
    reactor.run()
            
