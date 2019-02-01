import sys
from PySide import QtGui, QtCore
if QtCore.QCoreApplication.instance() is None:
    app = QtGui.QApplication(sys.argv)
    import qt4reactor
    qt4reactor.install() 
from twisted.internet.defer import Deferred, inlineCallbacks, returnValue
from twisted.internet import reactor
from labrad.wrappers import connectAsync
from qtutils.labelwidget import LabelWidget
from qtutils.labraderror import catch_labrad_error
from qtutils.lockwidget import DeviceLockWidget
from twisted.internet.defer import inlineCallbacks
from functools import partial

RANGE = (-10000000,10000000)
            
class DelayGeneratorWidget(QtGui.QWidget):
    def __init__(self,dg_name,default_dgs):
        QtGui.QWidget.__init__(self)
        self.dg_name = dg_name
        self.default_dgs = default_dgs
        self.init_gui()

    @inlineCallbacks
    def init_gui(self):
        layout = QtGui.QVBoxLayout()
        client = yield connectAsync()
        dg_server = client.delay_generator
        dg_names = yield dg_server.get_devices()
        dg_names.remove(self.dg_name)
        contexts = {}
        for dg_name in dg_names:
            context = dg_server.context()
            contexts[dg_name]= context
            dg_server.select_device(dg_name,context=context)            
        yield dg_server.select_device(self.dg_name)
        self.setLayout(layout)
        delay_label = QtGui.QLabel()
        layout.addWidget(delay_label)
        dg_server.on_new_delay.connect(lambda c, delay: delay_label.setNum(delay))
        delay_spin = QtGui.QSpinBox()
        layout.addWidget(delay_spin)
        delay_spin.setRange(*RANGE)
        dg_server.get_delay().addCallback(delay_label.setNum)
        set_delay_button = QtGui.QPushButton('set delay')
        shift_delay_button = QtGui.QPushButton('shift delay')
        button_row = QtGui.QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(set_delay_button)
        button_row.addWidget(shift_delay_button)
        button_row.addStretch()
        layout.addLayout(button_row)
        layout.addWidget(DeviceLockWidget(dg_server))
        
        @inlineCallbacks
        def set_delay(delay,shift):
            @inlineCallbacks
            def set_chained_delay(dg_name):
                context = contexts[dg_name]
                current_delay = yield dg_server.get_delay(context=context)
                dg_server.set_delay(current_delay+delay-old_delay,context=context)
            old_delay = yield dg_server.get_delay()
            if shift:
                delay += old_delay
            if delay < 1:
                QtGui.QMessageBox.error(
                    self,
                    'invalid delay',
                    'delay must be greater than 0'
                )
                returnValue(None)
            deferreds = []
            deferreds.append(dg_server.set_delay(delay))
            for row in range(cdw.count()):
                dg_name = cdw.item(row).text()
                deferreds.append(set_chained_delay(dg_name))
            for d in deferreds:
                yield d
                
        def on_clicked(shift):            
            catch_labrad_error(
                self,
                set_delay(delay_spin.value(),shift)
            )
        set_delay_button.clicked.connect(partial(on_clicked,False))
        shift_delay_button.clicked.connect(partial(on_clicked,True))
        chained_delays_widget = cdw = QtGui.QListWidget()
        unchained_delays_widget = udw = QtGui.QListWidget()
        for default_dg in self.default_dgs:
            dg_names.remove(default_dg)
            chained_delays_widget.addItem(default_dg)
        for dg_name in dg_names:
            unchained_delays_widget.addItem(dg_name)
        add_button = QtGui.QPushButton('add ^')
        remove_button = QtGui.QPushButton('remove v')
        def on_add():
            cdw.addItem(udw.takeItem(udw.currentRow()))
        def on_remove():
            udw.addItem(cdw.takeItem(cdw.currentRow()))
        add_button.clicked.connect(on_add)
        remove_button.clicked.connect(on_remove)
        layout.addWidget(QtGui.QLabel('chained dgs'))
        layout.addWidget(cdw)
        button_row = QtGui.QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(add_button)
        button_row.addWidget(remove_button)
        button_row.addStretch()
        layout.addLayout(button_row)
        layout.addWidget(QtGui.QLabel('unchained dgs'))
        layout.addWidget(udw)
        

class DelayGeneratorGroupWidget(QtGui.QWidget):
    def __init__(self,dg_server):
        QtGui.QWidget.__init__(self)
        layout = QtGui.QHBoxLayout()
        self.setLayout(layout)
        @inlineCallbacks
        def on_dg_names(dg_names):
            cxn = yield connectAsync()
            reg = cxn.registry
            yield reg.cd(['Clients','Delay Generator'])
            dir = yield reg.dir()
            masters = dir[1]
            for dg_name in dg_names:
                slaves = []
                if dg_name in masters:
                    slaves = yield reg.get(dg_name)
                layout.addWidget(
                    LabelWidget(
                        dg_name,
                        DelayGeneratorWidget(dg_name,slaves)
                    )
                )
        dg_server.get_devices().addCallback(on_dg_names)
    def closeEvent(self,event):
        event.accept()
        if reactor.running:
            reactor.stop()

if __name__ == '__main__':
    @inlineCallbacks
    def main():
        cxn = yield connectAsync()        
        dg_widget = DelayGeneratorGroupWidget(cxn.delay_generator)
        container.append(dg_widget)
        dg_widget.show()
    container = []
    reactor.callWhenRunning(main)
    reactor.run()
