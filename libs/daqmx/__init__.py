from ctypes import *
from daqmxconstants import constants
from util import DAQmxException
import numpy

dll = windll.LoadLibrary("nicaiu.dll")
"""handle to NI DAQmx c library"""

BUF_SIZE = 100000
"""size of string buffers for daqmx calls"""

TIMEOUT = 5.0

SUCCESS = 0
"""DAQmx return code for successful function call"""

# call a DAQmx function with arglist and raise a SitzException if error
def daqmx(f,args):
    """
    execute the DAQmx function f with specified args
    and raise exception with error description if
    return code indicates failure.
    
    @param f: DAQmx function from L{dll} to be called
        e.g. C{dll.DAQmxGetSysDevNames}
    @type f: C func        

    @param args: tuple of C data types to be
        passed to f.
    @type args: tuple

    @returns: C{None}    
    """
    result = f(*args)
    if result != SUCCESS:
        error = create_string_buffer(BUF_SIZE)
        dll.DAQmxGetErrorString(result,error,BUF_SIZE)
        raise DAQmxException(error.value)

def get_devices():
    """
    returns list of device identifiers

    @returns: list
    """
    devices = create_string_buffer(BUF_SIZE)
    daqmx(
        dll.DAQmxGetSysDevNames,
        (
            devices,
            BUF_SIZE
        )
    )
    return parseStringList(devices.value)

def parseStringList(stringList):
    return stringList.split(', ') if stringList else []

if __name__ == '__main__':
    for device in getDevices():
        print device
        for taskType, channels in getPhysicalChannels(device).items():
            print '\t' + TASK_TYPES[taskType]
            for channel in channels:
                print '\t\t' + channel
