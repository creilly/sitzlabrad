from jsonitems import JsonItem, LabelItem, IndexItem, KeyItem, ValueItem, AddItem, RemoveItem
from functools import partial

KEY_COLUMN = 0
VALUE_COLUMN = 1
ADD_COLUMN = 2
REMOVE_COLUMN = 3
TYPE_COLUMN = 4

COLUMNS = (
    KEY_COLUMN,
    VALUE_COLUMN,
    ADD_COLUMN,
    REMOVE_COLUMN,
    TYPE_COLUMN
)

APPEND = -1

class JsonNode:
    def __init__(self,items):        
        for item in items.values():
            item.set_node(self)

        self.items = {
            column:items.get(
                column,
                JsonItem()
            ) for column in COLUMNS 
        }
        self._is_moving = False

    def parent(self):
        return self.get_tree_item().parent().get_node()

    def get_row(self):
        return self.get_tree_item().row()

    def get_items(self):
        return [
            self.items[column] for column in COLUMNS
        ]

    def parent(self):
        return self.get_tree_item().parent().get_node()

    def child_node(self,row):
        return self.get_tree_item().child(row).get_node()

    def child_count(self):
        return self.get_tree_item().rowCount()

    def insert_node(self,row,node):
        tree_item = self.get_tree_item()
        if row is APPEND:
            tree_item.appendRow(
                node.get_items()
            )
        else:
            self.get_tree_item().insertRow(
                row,
                node.get_items()
            )

    def append_node(self,node):
        self.get_tree_item().appendRow(node.get_items())

    def remove_node(self,node):
        self.get_tree_item().takeRow(node.get_row())

    def get_tree_item(self):
        return self.get_items()[KEY_COLUMN]

    def start_move(self,row):
        self.node_to_move = self.child_node(row)
        self._is_moving = True

    def end_move(self,row):
        if row is -1:
            row = 0
        if row < self.child_count():
            reference_node = self.child_node(row)
        else:
            reference_node = None
        self.remove_node(self.node_to_move)
        self.insert_node(
            (
                APPEND
                if reference_node is None else
                reference_node.get_row()
            ),
            self.node_to_move
        )
        self._is_moving = False
        
    def is_moving(self):
        return self._is_moving

class ListNode(JsonNode):
    def __init__(self):
        JsonNode.__init__(
            self,
            {
                TYPE_COLUMN:LabelItem('list'),
                ADD_COLUMN:AddItem()
            }
        )

    def create_node(self):
        self.append_node(ListEntryNode(ValueNode()))

    def replace_node(self,old_node,json_object):
        row = old_node.get_row()
        self.remove_node(old_node)
        self.insert_node(
            row,
            parse_json_object(
                json_object,
                ListEntryNode
            )
        )

    def to_json(self):
        return [
            self.child_node(row).to_json()
            for row in range(self.child_count()) 
        ]

class DictNode(JsonNode):
    def __init__(self):
        JsonNode.__init__(
            self,
            {
                TYPE_COLUMN:LabelItem('dict'),
                ADD_COLUMN:AddItem(),
            }
        )

    def create_node(self):
        self.append_node(DictEntryNode('key',ValueNode()))
        
    def replace_node(self,old_node,json_object):
        row = old_node.get_row()
        key = old_node.get_key()
        self.remove_node(old_node)
        self.insert_node(
            row,
            parse_json_object(
                json_object,
                partial(
                    DictEntryNode,
                    key
                )
            )
        )

    def to_json(self):
        return {
            node.get_key():node.to_json()
            for node in [
                self.child_node(row)
                for row in range(self.child_count())
            ]
        }

class ValueNode(JsonNode):
    def __init__(self,value=None):
        JsonNode.__init__(
            self,
            {
                TYPE_COLUMN:LabelItem('value'),
                VALUE_COLUMN:ValueItem(value),
            }
        )
        self.value = value

    def to_json(self):
        return self.value

class WrapperNode(JsonNode):
    def __init__(self,node,items):
        self.target_node = node
        JsonNode.__init__(self,items)

    def create_node(self):
        self.target_node.create_node()

    def to_json(self):
        return self.target_node.to_json()

    def replace_node(self,old_node,json_object):
        self.target_node.replace_node(
            old_node,
            json_object
        )

class ListEntryNode(WrapperNode):
    def __init__(self,node):
        items = node.items
        items[KEY_COLUMN] = IndexItem()
        items[REMOVE_COLUMN] = RemoveItem()
        WrapperNode.__init__(self,node,items)

class DictEntryNode(WrapperNode):
    def __init__(self,key,node):
        items = node.items
        items[KEY_COLUMN] = KeyItem(key)        
        items[REMOVE_COLUMN] = RemoveItem()
        WrapperNode.__init__(self,node,items)

    def get_key(self):
        return str(self.items[KEY_COLUMN].text())

class ScanNode(ListEntryNode):
    def __init__(self,root_node,target_node):
        self.root_node = root_node
        ListEntryNode.__init__(self,target_node)

    def parent(self):
        return self.root_node

class RootNode(ListNode):
    def __init__(self,model):        
        self.model = model
        self.items = {
            KEY_COLUMN:model.invisibleRootItem()
        }        
        self.node_to_move = None
        self._is_moving = False

    def append_scan(self,json_scan):
        self.model.appendRow(
            parse_json_object(
                json_scan,
                partial(
                    ScanNode,
                    self
                )
            ).get_items()
        )

    def get_items(self):
        return [ self.items[KEY_COLUMN] ]

def parse_json_object(json_object,wrapper=None):
    json_type = type(json_object)
    if json_type is dict:
        dict_node = DictNode()
        if wrapper is not None:
            dict_node =  wrapper(dict_node)
        for key, entry in json_object.items():
            dict_node.append_node(
                parse_json_object(entry,partial(DictEntryNode,key))
            )
        return dict_node
    if json_type is list:
        list_node = ListNode()
        if wrapper is not None:
            list_node =  wrapper(list_node)
        for entry in json_object:
            list_node.append_node(
                parse_json_object(entry,ListEntryNode)
            )
        return list_node
    value_node = ValueNode(json_object)
    if wrapper is not None:
        value_node = wrapper(value_node)
    return value_node
