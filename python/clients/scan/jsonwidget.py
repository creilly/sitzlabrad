from PySide import QtCore, QtGui
from util import load_json, dump_json
import os

class JsonWidget(QtGui.QWidget):
    def __init__(self,model):
        QtGui.QWidget.__init__(self)
        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)

        tree = QtGui.QTreeView()
        layout.addWidget(tree)
        tree.setDragDropMode(tree.InternalMove)
        tree.setDragEnabled(True)
        tree.setAcceptDrops(True)
        tree.setDropIndicatorShown(True)
        tree.setSelectionBehavior(tree.SelectItems)
        def on_activated(index):
            if model.flags(index) & QtCore.Qt.ItemIsEditable:
                tree.edit(index)
        tree.activated.connect(on_activated)

        tree.setModel(model)
        column_widths = [
            model.column_width(column)
            for column in
            range(model.columnCount())
        ]
        for column, width in enumerate(column_widths):
            tree.setColumnWidth(
                column,
                width
            )
        self.resize(sum(column_widths)+20,500)

        def on_invalid_json():
            QtGui.QMessageBox.warning(
                self,
                'json error',
                'input must be valid json data'
            )
        model.invalid_json.connect(on_invalid_json)

        button_layout = QtGui.QHBoxLayout()
        layout.addLayout(button_layout)

        READ,WRITE = 0,1
        def get_file(mode=READ):
            return {
                READ:QtGui.QFileDialog.getOpenFileName,
                WRITE:QtGui.QFileDialog.getSaveFileName
            }[mode](self,dir='scans',filter='*.json')[0]

        def parse_file(filename):
            def fail():
                failure = (False,None)
                QtGui.QMessageBox.warning(
                    self,
                    'invalid json file',
                    'file was not list of json objects'
                )
                return failure            
            with open(filename,'r') as f:
                try:
                    json_object = load_json(f.read())
                    if type(json_object) is not list:
                        return fail()
                    return (True, json_object)
                except ValueError:                    
                    return fail()

        load_button = QtGui.QPushButton('load')
        button_layout.addWidget(load_button)
        def on_load():
            filename = get_file(mode=READ)
            if filename is None:
                return
            succeeded, json_scans = parse_file(filename)
            if not succeeded:
                return
            model.removeRows(0,model.rowCount())
            for json_scan in json_scans:
                model.append_scan(json_scan)
            update_filename_label(filename)
        self.load_scan = on_load
        load_button.clicked.connect(on_load)

        add_button = QtGui.QPushButton('add')
        button_layout.addWidget(add_button)
        def on_add():
            filename = get_file(mode=READ)
            if filename is None:
                return
            succeeded, json_scans = parse_file(filename)
            if not succeeded:
                return
            for json_scan in json_scans:
                model.append_scan(json_scan)            
        add_button.clicked.connect(on_add)

        new_button = QtGui.QPushButton('new')
        button_layout.addWidget(new_button)
        new_button.clicked.connect(model.create_scan)

        save_button = QtGui.QPushButton('save')
        button_layout.addWidget(save_button)
        def on_save():
            json_object = model.to_json()
            filename = get_file(WRITE)
            if filename is None:
                return
            with open(filename,'w') as f:
                f.write(dump_json(json_object))
            update_filename_label(filename)

        save_button.clicked.connect(on_save)
        
        button_layout.addStretch()

        def update_filename_label(filename):
            filename_label.setText(os.path.basename(filename))
        filename_label = QtGui.QLabel('unnamed')
        button_layout.addWidget(filename_label)
if __name__ == '__main__':
    import sys
    from jsonmodel import JsonModel
    app = QtGui.QApplication(sys.argv)
    json_model = JsonModel()
    json_model.append_scan(
        {
            'scan':'my scan'
        }
    )
    json_widget = JsonWidget(json_model)
    json_widget.setWindowTitle("json tree")
    json_widget.show()        
    sys.exit(app.exec_())
