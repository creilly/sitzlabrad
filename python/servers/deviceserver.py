from twisted.internet.defer import inlineCallbacks
from labrad.decorators import Setting
from labrad.server import LabradServer, Signal, setting
import functools
import inspect
from labrad.types import Error

############## instructions #####################
#
# device server is a base class for servers
# that manage multiple devices of identical 
# functionality (stepper motors, delay
# generators, etc.).
#
# to use device server, define a device class 
# that implements functionality of individual 
# devices. decorate any methods of the device 
# class that you would like to expose as labrad
# settings with the device_setting decorator,
# which works just like the setting decorator.
# additionally you can define signals for device
# classes using the DeviceSignal just as you 
# would for Signal and servers. clients that
# register for a signal will only receive signals
# emitted by their selected device.
#
# then define a device server that inherits from
# DeviceServer. set its device_class attribute to
# the device class you defined earlier. during
# server initialization, add instances of your
# device class (i.e. add devices) by using the
# device server's add_device method.
#
# to use the device server client-side, clients must first
# select a device. then when device settings are
# called by the client they will be executed by
# the selected device. device settings can be
# configured to be lockable by setting the
# device_setting_lockable flag on the device_setting
# decorator. clients can prevent other clients
# from accessing these settings for their
# selected device by calling the lock_device
# setting. unlock_device obviously releases the
# client's lock on their selected device.
#
# see testdeviceserver.py for a simple use case.
#
###################################################

NAME = 'Device Server'

ON_LOCKED_ID = 500
ON_LOCKED_NAME = 'on locked'
ON_UNLOCKED_ID = 501
ON_UNLOCKED_NAME = 'on unlocked'
GET_DEVICES =502
SELECT_DEVICE = 503
LOCK = 504
UNLOCK = 505
GET_SELECTED_DEVICE = 506
IS_LOCKED = 507
HAS_LOCK = 508

DEVICE_SETTING = '_device_setting'
DEVICE_SETTING_ID = '_device_setting_id'
DEVICE_SETTING_LOCKABLE = '_device_setting_lockable'
DEVICE_SETTING_PARAMS = '_device_setting_params'

class DeviceError(Error): pass
class DeviceServerError(Error):
    def __init__(self,device_id,device_error):
        Error.__init__(
            self,
            'error from device "%s": %s' % (device_id,device_error.msg)
        )
    
class NoDeviceSelectedError(Error):
    def __init__(self,context_id):
        Error.__init__(self,'context %s has no device selected' % (context_id,))

class DeviceLockedError(Error):
    def __init__(self,setting_id,setting_name,device_id,requesting_context,owning_context):
        Error.__init__(
            self,
            (
                'setting %d (%s) for device "%s" ' +
                'can not be accessed by context %s ' +
                'because it is locked by context %s'
            ) % (
                setting_id,
                setting_name,
                device_id,
                requesting_context,
                owning_context
            )
        )

class InvalidDeviceIDError(Error):
    def __init__(self,invalid_device_id):
        Error.__init__(
            self,
            'device id "%s" is not a valid device id' % invalid_device_id
        )

class DeviceAlreadyLockedError(Error):
    def __init__(self,device_id,requesting_context,owning_context):
        Error.__init__(
            self,
            (
                'device "%s" can not be locked by context %s because ' +
                'it is already locked by context %s'
            ) % (
                device_id,
                requesting_context,
                owning_context
            )
        )

class DeviceAlreadyUnlockedError(Error):
    def __init__(self,device_id):
        Error.__init__(
            self,
            'can not unlock device "%s" because it is already unlocked' % device_id
        )

class UnlockUnownedDeviceError(Error):
    def __init__(self,device_id,requesting_context,owning_context):
        Error.__init__(
            self,
            (
                'device "%s" can not be unlocked by context %s because ' +
                'it is owned by context %s'
            ) % (
                device_id,
                requesting_context,
                owning_context
            )
        )

class UnlockedDeviceNoOwnerError(Error):
    def __init__(self,device_id):
        Error.__init__(
            self,
            'device "%s" has no owner beacuse it is unlocked' % device_id
        )
        
class InvalidDeviceException(Exception):
    def __init__(self,device_class,invalid_device):
        Exception.__init__(
            self,
            'device %s is not instance of %s class' % (
                invalid_device,
                device_class
            )
        )

class DeviceClassUndefinedException(Exception):
    def __init__(self,server_class):
        Exception.__init__(
            self,
            (
                'no class device assigned for device server %s. ' +
                'set device server attribute "device_class" to ' +
                'appropriate device class'
            ) % server_class.__name__
        )
    
def device_setting(device_setting_id,device_setting_lockable=False,**device_setting_params):
    def decorator(f):
        setattr(f,DEVICE_SETTING,None)
        setattr(f,DEVICE_SETTING_ID,device_setting_id)
        setattr(f,DEVICE_SETTING_LOCKABLE,device_setting_lockable)
        setattr(f,DEVICE_SETTING_PARAMS,device_setting_params)
        return f
    return decorator

class DeviceSetting(Setting):
    def __init__(self, func, lr_ID, **params):        
        Setting.__init__(self, func, lr_ID, **params)
        setting_id = self.ID        
        def wrapped(self,c,*args,**kwargs):
            context_id = c.ID
            device_id = self.get_context_device_id(context_id)            
            device = self.get_device(device_id)
            try:
                return device.handle_request(setting_id,c,*args,**kwargs)
            except DeviceError, device_error:
                raise DeviceServerError(device_id,device_error)
        self.func = wrapped

def _device_setting(lr_ID, lr_name=None, returns=[], unflatten=True, **params):
    def decorator(func):
        try:
            handler = DeviceSetting(func, lr_ID, lr_name=lr_name, returns=returns, unflatten=unflatten, **params)
            func = handler.func  # might have gotten wrapped with inlineCallbacks
            func.ID = handler.ID
            func.name = handler.name
            func.accepts = handler.accepts
            func.returns = handler.returns
            func.handleRequest = handler.handleRequest
            func.getRegistrationInfo = handler.getRegistrationInfo
            return func
        except Exception:
            print 'Error in setting {} ({}):'.format(func.__name__, lr_ID)
            raise
    return decorator

class DeviceSignal:
    def __init__(self,ID,name,returns=[]):
        self.ID = ID
        self.name = name
        self.returns = returns

    def __call__(self,data=None):
        # no server attached if this is called so do nothing
        pass

class _DeviceSignal:
    def __init__(self,device_signal,parent):
        self.device_signal = device_signal
        self.parent = parent
        
    def __call__(self,data=None):
        self.device_signal.signal.__call__(self.parent,data)

class _DeviceSignal_(Signal):
    def __call__(self,device,data):
        server = self.parent
        context_ids = self.listeners.keys()
        device_context_ids = []
        for context_id in context_ids:
            if server.has_device_selected(context_id):
                selected_device_id = server.get_context_device_id(context_id)
                selected_device = server.get_device(selected_device_id)
                if selected_device is device:
                    device_context_ids.append(context_id)
        return Signal.__call__(self,data,device_context_ids)

class Device:
    on_locked = DeviceSignal(
        ON_LOCKED_ID,
        ON_LOCKED_NAME
    )
    on_unlocked = DeviceSignal(
        ON_UNLOCKED_ID,
        ON_UNLOCKED_NAME
    )
    
    def __init__(self):
        self.device_settings = {}
        for attr_name in dir(self):
            attr = getattr(self,attr_name)
            if hasattr(attr,DEVICE_SETTING):
                if inspect.isgeneratorfunction(attr):
                    attr = inlineCallbacks(attr)
                self.device_settings[getattr(attr,DEVICE_SETTING_ID)]=attr
            elif isinstance(attr,DeviceSignal):
                setattr(
                    self,
                    attr_name,
                    _DeviceSignal(attr,self)
                )
        self.owning_context = None

    def _is_locked(self):
        return self.owning_context is not None

    def get_owning_context(self):
        return self.owning_context

    def _lock(self,context_id):
        self.owning_context = context_id
        self.on_locked()

    def _unlock(self):
        self.owning_context = None
        self.on_unlocked()

    def _has_lock(self,context_id):
        return self.owning_context == context_id

    @device_setting(LOCK)
    def lock(self,c):
        context_id = c.ID
        if self._is_locked():
            requesting_context = context_id            
            owning_context = self.get_owning_context()
            raise DeviceError(
                'context %s can not lock device because device is owned by context %s' % (
                    requesting_context,
                    owning_context
                )
            )
        self._lock(context_id)

    @device_setting(UNLOCK)
    def unlock(self,c):
        context_id = c.ID
        if not self._is_locked():
            raise DeviceError('device already unlocked')
        if not self._has_lock(context_id):
            raise DeviceError('context %s can not unlock device because it does not own lock' % (context_id,))
        self._unlock()

    @device_setting(HAS_LOCK)
    def has_lock(self,c):
        context_id = c.ID
        if not self._is_locked():
            raise DeviceError('device is unlocked')
        return self._has_lock(context_id)

    @device_setting(IS_LOCKED)
    def is_locked(self,c):
        return self._is_locked()

    def handle_request(self,setting_id,c,*args,**kwargs):
        device_setting = self.device_settings[setting_id]
        if self._is_locked():
            context_id = c.ID
            if not self._has_lock(context_id):
                if getattr(device_setting,DEVICE_SETTING_LOCKABLE):
                    raise DeviceError(
                        (
                            'context %s can not access lockable setting %d because ' +
                            'device is locked by context %s'
                        ) % (
                            context_id,
                            setting_id,
                            self.get_owning_context()
                        )
                    )
        return device_setting(c,*args,**kwargs)

    def expire_context(self,context_id):
        if self._is_locked():
            if self.get_owning_context() == context_id:
                self._unlock()

class DeviceServer(LabradServer):
    sendTracebacks=False
    name = NAME

    @property
    def device_class(self):
        raise DeviceClassUndefinedException(type(self))

    def __init__(self):
        self.devices = {}
        self.context_device_ids = {}
        device_class = self.device_class
        for attribute_name in dir(device_class):
            attribute = getattr(device_class,attribute_name)
            if hasattr(attribute,DEVICE_SETTING):
                ds = attribute
                setattr(
                    self,
                    attribute_name,
                    _device_setting(
                        getattr(
                            ds,
                            DEVICE_SETTING_ID
                        ),
                        **getattr(
                            ds,
                            DEVICE_SETTING_PARAMS
                        )
                    )(ds)
                )
            if isinstance(attribute,DeviceSignal):
                device_signal = attribute
                signal = _DeviceSignal_(
                    device_signal.ID,
                    device_signal.name,
                    device_signal.returns
                )
                device_signal.signal=signal
                setattr(
                    self,
                    attribute_name,
                    signal
                )
        LabradServer.__init__(self)

    @setting(GET_DEVICES,returns='*s')
    def get_devices(self,c):
        """get identifiers of available devices"""
        return self.devices.keys()

    @setting(SELECT_DEVICE,device_id='s')
    def select_device(self,c,device_id):        
        context_id = c.ID
        if device_id not in self.devices:
            raise InvalidDeviceIDError(device_id)
        self._select_device(context_id,device_id)

    @setting(GET_SELECTED_DEVICE,returns='s')
    def get_selected_device(self,c):
        """get device identifier of selected device"""
        context_id = c.ID
        return self.get_context_device_id(context_id)

    def _select_device(self,context_id,device_id):        
        self.context_device_ids[context_id]=device_id 

    def get_device(self,device_id):
        return self.devices[device_id]

    def get_context_device_id(self,context_id):
        if not self.has_device_selected(context_id):
            raise NoDeviceSelectedError(context_id)
        return self.context_device_ids[context_id]

    def add_device(self,device_id,device,*args,**kwargs):
        if not isinstance(device,self.device_class):
            raise InvalidDeviceException(
                self.device_class,
                device                
            )
        self.devices[device_id]=device

    def has_device_selected(self,context_id):
        return context_id in self.context_device_ids

    def expireContext(self,c):
        context_id = c.ID
        for device in self.devices.values():
            device.expire_context(context_id)

