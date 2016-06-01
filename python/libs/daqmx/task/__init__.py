from daqmx import *

class EmptyTaskException(Exception):
    args = ['task must have at least one channel to determine type']

class UnitsException(Exception):
    args = ['only analog input or analog output tasks have channels with units']

class Task(object):
    """
    base class from which useful daqmx task
    classes inherit.
    """
    AI,AO,DI,DO,CI,CO,EMPTY=0,1,2,3,4,5,6
    TASK_TYPES = (AI,AO,DI,DO,CI,CO,EMPTY)

    def __init__(self,*channels):
        """
        load a global task into memory and optionally initialize with global channel
        """
        handle = c_uint32(0)
        daqmx(
            dll.DAQmxCreateTask,
            (
                None,
                byref(handle)
            )
        )
        self.handle = handle.value
        for channel in channels:
            self.add_channel(channel)
        
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

    @classmethod
    def get_global_tasks(cls):
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
        global_tasks = parseStringList(global_tasks.value)
        task_dict = {task_type:[] for task_type in cls.TASK_TYPES}
        for task_name in global_tasks:
            task = cls(task_name)
            task_dict[task.get_type()].append(task_name)
        return task_dict

    def get_type(self):
        channels = self.get_channels()
        if not channels:
            return self.EMPTY
        return self.get_channel_type(channels[0])

    @classmethod
    def get_channel_type(cls,channel):
        handle = c_uint32(0)
        daqmx(
            dll.DAQmxCreateTask,
            (
                '',
                byref(handle)
            )            
        )
        handle = handle.value
        daqmx(
            dll.DAQmxAddGlobalChansToTask,
            (
                handle,
                channel
            )
        )
        channel_type = c_uint32(0)
        daqmx(
            dll.DAQmxGetChanType,
            (
                handle, 
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
                global_channels,
                BUF_SIZE
            )
        )
        global_channels = parseStringList(global_channels.value)
        channel_dict = {
            task_type:[] for task_type in cls.TASK_TYPES
        }
        for channel in global_channels:
            channel_dict[cls.get_channel_type(channel)].append(channel)
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

    def get_units(self):
        task_type = self.get_type()
        if task_type not in (self.AI,self.AO):
            raise UnitsException()
        units = {}
        for channel in self.get_channels():
            measurement_type = c_int32(0)
            daqmx(
                {
                    self.AI:dll.DAQmxGetAIMeasType,
                    self.AO:dll.DAQmxGetAOOutputType
                }[task_type],
                (
                    self.handle,
                    channel,
                    byref(measurement_type)
                )
            )
            measurement_type = measurement_type.value
            unit_type = c_int32(0)
            daqmx(
                {
                    constants['DAQmx_Val_Voltage']:{
                        self.AI:dll.DAQmxGetAIVoltageUnits,
                        self.AO:dll.DAQmxGetAOVoltageUnits,
                    }[task_type],
                    constants['DAQmx_Val_Current']:{
                        self.AI:dll.DAQmxGetAICurrentUnits,
                        self.AO:dll.DAQmxGetAOCurrentUnits,
                    }[task_type],
                    constants['DAQmx_Val_Temp_TC']:dll.DAQmxGetAITempUnits
                }[measurement_type],
                (
                    self.handle,
                    channel,
                    byref(unit_type)
                )
            )
            unit_type = unit_type.value
            unit_types = {
                constants['DAQmx_Val_Volts']:'volts',
                constants['DAQmx_Val_Amps']:'amps',
                constants['DAQmx_Val_DegC']:'degs C',
                constants['DAQmx_Val_DegF']:'degs F',
                constants['DAQmx_Val_Kelvins']:'degs K',
            }
            if unit_type in unit_types:
                units[channel] = unit_types[unit_type]
            elif unit_type == constants['DAQmx_Val_FromCustomScale']:
                scale_name = create_string_buffer(BUF_SIZE)
                daqmx(
                    {
                        self.AI:dll.DAQmxGetAICustomScaleName,
                        self.AO:dll.DAQmxGetAOCustomScaleName,
                    }[task_type],
                    (
                        self.handle,
                        channel,
                        scale_name,
                        BUF_SIZE
                    )
                )
                scaled_units = create_string_buffer(BUF_SIZE)
                daqmx(
                    dll.DAQmxGetScaleScaledUnits,
                    (
                        scale_name.value,
                        scaled_units,
                        BUF_SIZE
                    )
                )
                units[channel] = scaled_units.value
            else:
                units[channel] = 'arb'
        return units
            

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


