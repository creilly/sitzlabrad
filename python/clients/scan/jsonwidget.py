from PySide import QtCore, QtGui
import json

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
            }[mode](self)[0]

        def parse_file(filename):
            with open(filename,'r') as f:
                try:
                    json_object = json.load(f)
                    return (True, json_object)
                except ValueError:
                    QtGui.QMessageBox.warning(
                        self,
                        'invalid json file',
                        'file was not list of json objects'
                    )
                    return (False, None)

        def get_scans_from_file():
            failure = (False,None)
            filename = get_file()
            if filename is None:
                return failure
            succeeded, json_object = parse_file(filename)
            if not succeeded:
                return failure
            return (True,json_object)

        load_button = QtGui.QPushButton('load')
        button_layout.addWidget(load_button)
        def on_load():
            succeeded, json_scans = get_scans_from_file()
            if not succeeded:
                return
            model.removeRows(0,model.rowCount())
            for json_scan in json_scans:
                model.append_scan(json_scan)            
        load_button.clicked.connect(on_load)

        add_button = QtGui.QPushButton('add')
        button_layout.addWidget(add_button)
        def on_add():
            succeeded, json_scans = get_scans_from_file()
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
                f.write(json.dumps(json_object))
        save_button.clicked.connect(on_save)
        
        button_layout.addStretch()

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
