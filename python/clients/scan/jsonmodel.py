from PySide import QtCore, QtGui
from jsonnodes import KEY_COLUMN, VALUE_COLUMN, ADD_COLUMN, REMOVE_COLUMN, TYPE_COLUMN, COLUMNS, RootNode
from util import byteify

column_names = {
    KEY_COLUMN:'key',
    VALUE_COLUMN:'value',
    ADD_COLUMN:'add',
    REMOVE_COLUMN:'remove',
    TYPE_COLUMN:'type'
}

class JsonModel(QtGui.QStandardItemModel):
    invalid_json = QtCore.Signal()
    def __init__(self):
        QtGui.QStandardItemModel.__init__(self)
        self.root_node = RootNode(self)
        self.setHorizontalHeaderLabels(
            [
                column_names[column]
                for column in COLUMNS
            ]
        )

    def append_scan(self,json_scan):
        self.root_node.append_scan(byteify(json_scan))

    def create_scan(self):
        self.root_node.append_scan({})

    def mimeData(self,indexes):
        node = self.itemFromIndex(indexes[0]).get_node()
        parent = node.parent()
        parent.start_move(node.get_row())
        return QtGui.QStandardItemModel.mimeData(self,indexes)
    def dropMimeData(self,data,action,row,column,parent):
        item = self.itemFromIndex(parent)
        if item is None:
            node = self.root_node
        else:
            node = item.get_node()
        node.end_move(row)
        return False

    def flags(self,index):
        item = self.itemFromIndex(index)
        if item:
            return item.flags()
        else:
            if self.root_node.is_moving():
                return QtCore.Qt.ItemIsDropEnabled
            else:
                return QtCore.Qt.NoItemFlags

    def supportedDragActions(self):
        return QtCore.Qt.MoveAction

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction

    def to_json(self):
        return self.root_node.to_json()

    # just to help the view
    def column_width(self,column):
        return {
            KEY_COLUMN:250,
            VALUE_COLUMN:250,
            ADD_COLUMN:50,
            REMOVE_COLUMN:70,
            TYPE_COLUMN:100
        }[column]

