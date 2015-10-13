from PySide import QtGui, QtCore
import json

class JsonItem(QtGui.QStandardItem):
    def __init__(self,text=None):
        QtGui.QStandardItem.__init__(self)
        self.setCheckable(False)
        self.setEditable(False)
        self.setDropEnabled(False)
        self.setDragEnabled(True)
        font = self.font()
        font.setPointSize(20)
        self.setFont(font)
        if text is not None:
            self.setText(text)

    def set_node(self,node):
        self.node = node

    def get_node(self):
        return self.node

    def has_node(self):
        return hasattr(self,'node')

    def flags(self):
        flags = QtGui.QStandardItem.flags(self)
        if self.has_node() and self.get_node().is_moving():
            flags = flags | QtCore.Qt.ItemIsDropEnabled
        return flags

class LabelItem(JsonItem): pass
        
class IndexItem(JsonItem):
    def data(self,role):
        if role == QtCore.Qt.DisplayRole:
            return str(self.row())
        return JsonItem.data(self,role)

class KeyItem(JsonItem):
    def __init__(self,key):
        JsonItem.__init__(self)
        self.setEditable(True)
        self.setText(key)

class ValueItem(JsonItem):
    def __init__(self,value):
        JsonItem.__init__(self)
        self.setEditable(True)
        JsonItem.setData(
            self,
            json.dumps(value),
            QtCore.Qt.DisplayRole
        )
    def setData(self,data,role):
        if role == QtCore.Qt.EditRole:
            self.on_value_changed(data)
            return
        JsonItem.setData(self,data,role)
    def on_value_changed(self,text):
        try:
            node = self.get_node()
            node.parent().replace_node(
                node,
                json.loads(text)
            )
        except ValueError:
            self.model().invalid_json.emit()

class CheckItem(JsonItem):
    def __init__(self):
        JsonItem.__init__(self)
        self.setCheckable(True)

    def setData(self,data,role):
        if role == QtCore.Qt.CheckStateRole and data:
            return self.on_checked()
        return JsonItem.setData(self,data,role)

class AddItem(CheckItem):
    def __init__(self):
        CheckItem.__init__(self)
        self.setBackground(
            QtGui.QBrush(
                QtGui.QColor(150,255,150)
            )
        )
    def on_checked(self):
        self.get_node().create_node()
    
class RemoveItem(CheckItem):
    def __init__(self):
        CheckItem.__init__(self)
        self.setBackground(
            QtGui.QBrush(
                QtGui.QColor(255,150,150)
            )
        )

    def on_checked(self):
        node = self.get_node()
        node.parent().remove_node(node)
