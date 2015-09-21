from QtCore import Signal
class ScanItemWidget(QtGui.QWidget):
    def get_axis_label(self):
        pass
class ScanInputWidget(ScanItemWidget):
    def set_input(self,input):
        pass
class GroupScanItemWidget(QtGui.QWidget):
    def add_scan_item_widget(self,widget): pass
    def remove_scan_item_widget(self,widget): pass
    def get_axis_label(self): pass
class GroupScanInputWidget(GroupScanItemWidget):
    def set_input(self,input): pass
    
class ScanOutputWidget(ScanItemWidget):
    def get_output(self):
        pass
class GroupInputWidget(Qt)
class ScanWidget(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        layout = QtGui.QHBoxLayout()
        plot_widget = PlotWidget()
        plot = plot_widget.plot()
        layout.addWidget(plot_widget)
        control_layout = QtGui.QVBoxLayout()
        layout.addLayout(control_layout)
        
