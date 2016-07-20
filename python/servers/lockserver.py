from labrad.decorators import Setting
from labrad.server import LabradServer, Signal, setting
import functools
import inspect

LOCKABLE = '_lockable'

LOCK_SETTING_ID = 410

UNLOCK_SETTING_ID = 411

IS_SETTING_LOCKED_ID = 412

HAS_SETTING_LOCK_ID = 413

IS_SETTING_LOCKABLE_ID = 414

OWNING_CONTEXT_ID = 415

GET_CONTEXT_ID = 416

ON_SETTING_LOCKED_ID = 417

ON_SETTING_UNLOCKED_ID = 418

ON_SETTING_LOCKED_NAME = 'on_setting_locked'

ON_SETTING_UNLOCKED_NAME = 'on_setting_unlocked'

class LockedException(Exception):    
    def __init__(
            self,
            setting_id,
            setting_name,
            requesting_context,
            owning_context
    ):
        Exception.__init__(
            self,
            'context %s can not access setting %s (id %d) \
            because it is locked by context %s' % (
                requesting_context,
                setting_name,
                setting_id,
                owning_context
            )
        )

class SettingNotLockableException(Exception):
    def __init__(self,setting_id,setting_name):
        Exception.__init__(
            self,
            'setting %s (id %d) does not have locking enabled' % (
                setting_id,
                setting_name
            )
        )

class SettingAlreadyLockedException(Exception):
    def __init__(
            self,
            setting_id,
            setting_name,
            requesting_context,
            owning_context
    ):
        Exception.__init__(
            self,
            'setting %s (id %d) can not be locked by context %s \
            because it is already locked by context %s' % (
                setting_name, 
                setting_id, 
                requesting_context, 
                owning_context
            )
        )

class UnlockUnlockedSettingException(Exception):
    def __init__(
            self,
            setting_id,
            setting_name
    ):
        Exception.__init__(
            self,
            'setting %s (id %d) is already unlocked' % (
                setting_name,
                setting_id                
            )
        )

class UnlockUnownedSettingException(Exception):
    def __init__(
            self,
            setting_id,
            setting_name,
            requesting_context,
            owning_context        
    ):
        Exception.__init__(
            self,
            'setting %s (id %d) can not be unlocked by \
            context %s because it is locked by context %s' % (
                setting_name,
                setting_id,
                requesting_context,
                owning_context
            )
        )

class SettingNotLockedException(Exception):
    def __init__(
            self,
            setting_id,
            setting_name
    ):
        Exception.__init__(
            self,
            'setting %s (id %d) has no owning context because \
            it is unlocked' % (
                setting_name,
                setting_id                
            )
        )
        
class LockableSetting(Setting):
    def __init__(self, func, lr_ID, lr_name, returns, unflatten, **params):        
        Setting.__init__(self, func, lr_ID, lr_name, returns, unflatten, **params)
        func = self.func
        this = self
        def wrapped(self,c,*args,**kwargs):
            if not self._can_access_setting(c.ID,this.ID):
                raise LockedException(this.ID,this.name,c.ID,self._owning_context(this.ID))
            return func(self,c,*args,**kwargs)
        self.func = wrapped

def lockable_setting(lr_ID, lr_name=None, returns=[], unflatten=True, **params):
    def decorator(func):
        try:
            handler = LockableSetting(func, lr_ID, lr_name, returns, unflatten, **params)
            func = handler.func  # might have gotten wrapped with inlineCallbacks
            func.ID = handler.ID
            func.name = handler.name
            func.accepts = handler.accepts
            func.returns = handler.returns
            func.handleRequest = handler.handleRequest
            func.getRegistrationInfo = handler.getRegistrationInfo
            setattr(func,LOCKABLE,None)
            return func
        except Exception:
            print 'Error in setting {} ({}):'.format(func.__name__, lr_ID)
            raise
    return decorator
    
class LockServer(LabradServer):
    on_setting_locked = Signal(
        ON_SETTING_LOCKED_ID,
        ON_SETTING_LOCKED_NAME,
        'w'
    )
    on_setting_unlocked = Signal(
        ON_SETTING_UNLOCKED_ID,
        ON_SETTING_UNLOCKED_NAME,
        'w'
    )
    def __init__(self):
        self.locked_settings = {}
        LabradServer.__init__(self)

    @setting(LOCK_SETTING_ID,setting_id='w',returns=[])
    def lock_setting(self,c,setting_id):    
        if not hasattr(
                self.settings[setting_id],
                LOCKABLE
        ):
            raise SettingNotLockableException(
                setting_id,
                self.settings[setting_id].name,
            )
        if setting_id in self.locked_settings:
            raise SettingAlreadyLockedException(
                setting_id,
                self.settings[setting_id].name,
                c.ID,
                self.locked_settings[setting_id]
            )
        self._lock_setting(c.ID,setting_id)

    def _lock_setting(self,context_id,setting_id):
        self.locked_settings[setting_id]=context_id
        self.on_setting_locked((setting_id,context_id))

    @setting(UNLOCK_SETTING_ID,setting_id='w')
    def unlock_setting(self,c,setting_id):
        if setting_id not in self.locked_settings:
            raise UnlockUnlockedSettingException(
                setting_id,
                self.settings[setting_id].name
            )
        if self.locked_settings[setting_id] != c.ID:
            raise UnlockUnownedSettingException(
                setting_id,
                self.settings[setting_id],
                c.ID,
                self.locked_settings[setting_id]
            )
        self._unlock_setting(setting_id)

    def _unlock_setting(self,setting_id):
        del self.locked_settings[setting_id]
        self.on_setting_unlocked(setting_id)

    @setting(IS_SETTING_LOCKED_ID,setting_id='w',returns='b')
    def is_setting_locked(self,c,setting_id):
        return setting_id in self.locked_settings

    @setting(HAS_SETTING_LOCK_ID,setting_id='w',returns='b')
    def has_setting_lock(self,c,setting_id):
        if setting_id not in self.locked_settings:
            raise SettingNotLockedException(
                setting_id,
                self.settings[setting_id].name
            )
        return self.locked_settings[setting_id]==c.ID

    @setting(IS_SETTING_LOCKABLE_ID,setting_id='w',returns='b')
    def is_setting_lockable(self,c,setting_id):
        return hasattr(self.settings[setting_id],LOCKABLE)

    @setting(OWNING_CONTEXT_ID,setting_id='w')
    def owning_context(self,c,setting_id):
        if setting_id not in self.locked_settings:
            raise SettingNotLockedException(
                setting_id,
                self.settings[setting_id].name
            )
        return self._owning_context(setting_id)

    def _owning_context(self,setting_id):
        return self.locked_settings[setting_id]
    
    @setting(GET_CONTEXT_ID,returns='(ww)')
    def get_context(self,c):
        return c.ID

    def _can_access_setting(self,context_id,setting_id):
        return (
            setting_id not in self.locked_settings
            or
            self.locked_settings[setting_id] == context_id
        )

    def expireContext(self,c):
        for setting_id in [
                setting_id 
                for setting_id, context_id in 
                self.locked_settings.items() 
                if context_id == c.ID
        ]:
            self._unlock_setting(setting_id)
        
