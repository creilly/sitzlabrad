from PySide import QtCore, QtGui

class JSONItem:
    def __init__(self):
        self._parent = None
    def parent(self):
        return self._parent
    def set_parent(self,parent):
        self._parent = parent
    def row(self):
        parent = self.parent()
        if parent is None:
            return 0        
        return parent.child_row(self)
    def is_reorderable(self):
        return False
    
class ValueItem(JSONItem):
    def __init__(self):
        JSONItem.__init__(self)
        self.value = None

    def set_value(self,value):
        self.value = value

    def get_value(self):
        return self.value

    def data(self,column):
        return {
            TREE_COLUMN:'value',
            VALUE_COLUMN:json.dumps(self.value)
        }.get(column,None)
    
    def set_data(self,column,data):
        try:
            self.value = json.loads(data)
        except ValueError:
            return False
        return True

    def is_editable(self,column):
        return {
            VALUE_COLUMN:True
        }.get(column,False)

    def child_count(self):
        return 0

    def to_json(self):
        return self.value

class ContainerItem(JSONItem):
    def __init__(self,item):
        JSONItem.__init__(self)
        self.item = item

    def set_data(self,column,data):
        if column is VALUE_COLUMN:
            try:
                self.set_item(parse_json_object(json.loads(data)))
            except ValueError:
                return False
            return True
        return False

    def data(self,column):
        return self.item.data(column)

    def is_editable(self,column):
        return self.item.is_editable(column)

    def child_count(self):
        return self.item.child_count()

    def child(self,row):
        return self.item.child(row)

    def get_item(self):
        return self.item 

    def set_item(self,item):
        self.item = item

class EntryItem(ContainerItem):
    def __init__(self,key,item):
        ContainerItem.__init__(self,item)
        self.key = key

    def set_data(self,column,data):
        if column is KEY_COLUMN:
            self.set_key(data)
            return True
        return ContainerItem.set_data(self,column,data)

    def data(self,column):
        if column is KEY_COLUMN:
            return self.key
        return ContainerItem.data(self,column)

    def is_editable(self,column):
        if column is KEY_COLUMN:
            return True
        return ContainerItem.is_editable(self,column)

    def get_key(self):
        return self.key

    def set_key(self,key):
        self.key = key

class ListEntryItem(ContainerItem):
    def data(self,column):
        if column is KEY_COLUMN:
            return str(self.row())
        return ContainerItem.data(self,column)

    def is_editable(self,column):
        if column is KEY_COLUMN:
            return False
        return ContainerItem.is_editable(self,column)

class ListItem(JSONItem):
    def __init__(self):
        JSONItem.__init__(self)
        self.items = []

    def data(self,column):
        return {
            TREE_COLUMN:'list'
        }.get(column,None)
     
    def child(self,row):
        return self.items[row]

    def add_item(self,item):
        list_entry_item = ListEntryItem(item)
        list_entry_item.set_parent(self)
        self.items.append(list_entry_item)

    def remove_item(self,item):
        self.items.remove(item)

    def insert_item(self,row,item):
        item.set_parent(self)
        self.items.insert(row,item)

    def child_count(self):
        return len(self.items)

    def child_row(self,child):
        return self.items.index(child)

    def is_editable(self,column):
        return False

    def is_reorderable(self):
        return True

    def to_json(self):
        return [ item.to_json()  for item in self.items ]

class DictItem(JSONItem):
    def __init__(self):
        JSONItem.__init__(self)
        self.entries = []        

    def child(self,row):
        return self.entries[row]

    def add_entry(self,key,item):
        entry = EntryItem(key,item)
        entry.set_parent(self)
        self.entries.append(entry)

    def child_count(self):
        return len(self.entries)

    def data(self,column):
        return {
            TREE_COLUMN:'dict',
        }.get(column,None)

    def child_row(self,child):
        return self.entries.index(child)

    def is_editable(self,column):
        return False

    def to_json(self):
        return {entry.get_key():entry.get_item().to_json() for entry in self.entries}

def parse_json_object(json_object):
    json_type = type(json_object)
    if json_type is dict:
        dict_item = DictItem()
        for key, data in json_object.items():
            dict_item.add_entry(key,parse_json_object(data))
        return dict_item
    elif json_type is list:
        list_item = ListItem()
        for data in json_object:
            list_item.add_item(parse_json_object(data))
        return list_item
    else:
        value_item = ValueItem()
        value_item.set_value(json_object)
        return value_item

TREE_COLUMN = 0
KEY_COLUMN = 1
VALUE_COLUMN = 2
ADD_COLUMN = 3
REMOVE_COLUMN = 4
COLUMNS = (TREE_COLUMN,KEY_COLUMN,VALUE_COLUMN,ADD_COLUMN,REMOVE_COLUMN)

class JSONModel(QtCore.QAbstractItemModel):
    def __init__(self,json_object={'key':'value'}):
        QtCore.QAbstractItemModel.__init__(self)
        self.item_to_move = None
        self.set_root_item(json_object)

    def columnCount(self, parent):
        return len(COLUMNS)

    def headerData(self,section,orientation,role):
        if role != QtCore.Qt.DisplayRole:
            return None
        return {
            TREE_COLUMN:'tree',
            KEY_COLUMN:'key',
            VALUE_COLUMN:'value',
            ADD_COLUMN:'add',
            REMOVE_COLUMN:'remove'
        }[section]

    def setData(self,index,value,role):
        self.layoutAboutToBeChanged.emit()
        result = index.internalPointer().set_data(
            index.column(),value
        )
        self.layoutChanged.emit()
        return result

    def data(self, index, role):
        if not index.isValid():
            return None

        if role != QtCore.Qt.DisplayRole:
            return None

        item = index.internalPointer()

        return item.data(index.column())

    def flags(self, index):
        if not index.isValid():
            item = self.root_item
        else:
            item = index.internalPointer()
        
        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

        if item.is_editable(index.column()):
            flags = flags | QtCore.Qt.ItemIsEditable

        parent = item.parent()

        if parent is not None and parent.is_reorderable():
            flags = flags | QtCore.Qt.ItemIsDragEnabled
            
        if self.item_to_move and item is self.item_to_move.parent():
            flags = flags | QtCore.Qt.ItemIsDropEnabled

        return flags

    def index(self, row, column, parent_index):        
        if not self.hasIndex(row, column, parent_index):
            return QtCore.QModelIndex()

        if not parent_index.isValid():
            parent_item = self.root_item
        else:
            parent_item = parent_index.internalPointer()
        return self.createIndex(row, column, parent_item.child(row))

    def parent(self, index):
        child_item = index.internalPointer()
        parent_item = child_item.parent()

        if parent_item is None:
            return QtCore.QModelIndex()
            
        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, parent):
        if parent.column() > 0:
            return 0
            
        if not parent.isValid():
            parent_item = self.root_item
        else:
            parent_item = parent.internalPointer()

        return parent_item.child_count()
        
    def mimeData(self,indexes):
        self.item_to_move = indexes[0].internalPointer()
        return QtCore.QAbstractItemModel.mimeData(self,indexes)

    def dropMimeData(self,data,action,row,column,parent_index):
        return self.insertRows(row,1,parent_index)

    def insertRows(self,row,count,parent_index):
        item = self.item_to_move
        if not parent_index.isValid():
            parent = self.root_item
        else:
            parent = parent_index.internalPointer()
        neighbor = parent.child(row)
        self.beginRemoveRows(parent_index,item.row(),item.row())
        parent.remove_item(item)
        self.endRemoveRows()
        self.beginInsertRows(parent_index,neighbor.row(),neighbor.row())
        parent.insert_item(neighbor.row(),item)
        self.endInsertRows()        
        return True
        
    def removeRows(self,row,count,parent):
        return True

    def supportedDragActions(self):
        return QtCore.Qt.MoveAction

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction

    def set_root_item(self,json_object):
        self.root_item = parse_json_object(json_object)

if __name__ == '__main__':

    import sys
    import json
    app = QtGui.QApplication(sys.argv)

    model = JSONModel()

    view = QtGui.QTreeView()
    view.setDragDropMode(view.InternalMove)
    view.setDragEnabled(True)
    view.setAcceptDrops(True)
    view.setDropIndicatorShown(True)
    view.setModel(model)
    view.setWindowTitle("Simple Tree Model")
    view.show()
    sys.exit(app.exec_())
