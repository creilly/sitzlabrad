from deviceserver import device_setting, DeviceServer, Device, DeviceSignal

NAME = 'Test Device'

class TestDevice(Device):
    on_salivation = DeviceSignal(15,'on salivation')
    def __init__(self):
        Device.__init__(self)
        self.number = 0
    @device_setting(10,number='i',returns='i')
    def increment(self,c,number):
        """adds one to specified number"""
        return number + 1

    @device_setting(11,number='i',returns='i')
    def decrement(self,c,number):
        """subtracts one from specified number"""
        return number - 1

    @device_setting(12,returns='i')
    def get_number(self,c):
        return self.number

    @device_setting(13,device_setting_lockable=True,number='i')
    def set_number(self,c,number):
        self.number = number

    @device_setting(14)
    def ring_bell(self,c):
        self.on_salivation()

class TestDeviceServer(DeviceServer):
    name = NAME
    device_class = TestDevice
    def initServer(self):
        self.add_device('dev 1',TestDevice())
        self.add_device('dev 2',TestDevice())
        DeviceServer.initServer(self)        

__server__ = TestDeviceServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
