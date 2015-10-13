import os
from os import path
from datetime import datetime

POOH_DATA_PATH = 'z:/data/pooh/'

def get_filename(folders=None,description=None,extension='.dat'):
    if folders is None: 
        folders = []
    filepath = path.join(
        POOH_DATA_PATH,
        datetime.now().strftime("%Y-%m-%d"),
        *folders
    )
    if not path.exists(filepath):
        os.makedirs(filepath)
    time = datetime.now().strftime("%H%M%S")
    return os.path.join(
        filepath,
        (
            '_'.join(
                (
                    time,
                    description,
                    extension
                ) if description is not None else (
                    time,
                    extension
                )
            ) 
        )
    )
def get_file_dialog():
    import Tkinter, tkFileDialog

    root = Tkinter.Tk()
    root.withdraw()

    return tkFileDialog.askopenfilename()
