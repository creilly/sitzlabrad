from daqmx import *

class EmptyTaskException(Exception):
    args = ['task must have at least one channel to determine type']

class Task(object):
    """
    base class from which useful daqmx task
    classes inherit.
    """
    AI,AO,DI,DO,CI,CO=0,1,2,3,4,5    

    def __init__(self,name):
        """
        load a global task into memory
        """
        handle = c_uint32(0)
        daqmx(
            dll.DAQmxLoadTask,
            (
                name, 
                byref(handle)
            )
        )
        self.handle = handle.value
        
    def add_channel(self,name):
        """
        add global channel into memory
        """
        daqmx(
            dll.DAQmxAddGlobalChansToTask,
            (
                self.handle, 
                name
            )
        )

    @staticmethod
    def get_global_tasks():
        """
        get list of global channels that can be added tasks of this type

        @returns: list of virtual channel identifiers
        """
        global_tasks = create_string_buffer(BUF_SIZE)
        daqmx(
            dll.DAQmxGetSysTasks,
            (
                global_tasks,
                BUF_SIZE
            )
        )
        return parseStringList(global_tasks.value)

    def get_type(self):
        channels = self.get_channels()
        if not channels:
            raise EmptyTaskException
        return self.get_channel_type(self.get_channels[0])

    def get_channel_type(self,channel):
        channel_type = c_uint32(0)
        daqmx(
            DAQmxGetChanType,
            (
                self.handle, 
                channel, 
                byref(channel_type)
            )
        )
        return {
            constants['DAQmx_Val_AI']:cls.AI,
            constants['DAQmx_Val_AO']:cls.AO,
            constants['DAQmx_Val_DI']:cls.DI,
            constants['DAQmx_Val_DO']:cls.DO,
            constants['DAQmx_Val_CI']:cls.CI,
            constants['DAQmx_Val_CO']:cls.CO,
        }[channel_type.value]

    @classmethod
    def get_global_channels(cls):
        """
        get list of global channels that can be added tasks of this type

        @returns: list of virtual channel identifiers
        """
        global_channels = create_string_buffer(BUF_SIZE)
        daqmx(
            dll.DAQmxGetSysGlobalChans,
            (
                self.handle,
                global_channels,
                BUF_SIZE
            )
        )
        global_channels = parseStringList(global_channels.value)
        channel_dict = {
            task_type:[] for task_type in (cls.AI,cls.AO,cls.DI,cls.DO)
        }
        for channel in global_channels:
            channel_dict[self.get_channel_type(channel)].append(channel)
        return channel_dict

    def get_channels(self):
        """
        get list of channels belonging to this task

        @returns: list of virtual channel identifiers
        """        
        channels = create_string_buffer(BUF_SIZE)
        daqmx(
            dll.DAQmxGetTaskChannels,
            (
                self.handle,
                channels,
                BUF_SIZE
            )
        )
        return parseStringList(channels.value)


    def clear_task(self):
        daqmx(
            dll.DAQmxClearTask,
            (
                self.handle,
            )
        )

    def is_done(self):
        is_done = c_uint32(0)
        daqmx(
            dll.DAQmxIsTaskDone,
            (
                self.handle,
                byref(is_done)
            )                
        )
        return bool(is_done.value)

    
