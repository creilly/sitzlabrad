from PySide import QtGui
from twisted.internet.defer import inlineCallbacks, returnValue
from labrad.types import Error

@inlineCallbacks
def catch_labrad_error(parent,deferred):
    try:
        result = yield deferred
    except Error, e:
        QtGui.QMessageBox.warning(parent,'labrad error',e.msg)
        returnValue((False,None))
    returnValue((True,result))
