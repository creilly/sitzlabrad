import os
from os import path
from datetime import datetime

default_directory = os.environ.get('DATA','./') # default to working dir

def get_datetime():
    return datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

def get_filename(directory=None,folders=None,description=None,extension='.dat'):
    if folders is None: 
        folders = []
    if directory is None:
        directory = default_directory
    filepath = path.join(
        default_directory,
        datetime.now().strftime("%Y-%m-%d"),
        *folders
    )
    if not path.exists(filepath):
        os.makedirs(filepath)
    time = datetime.now().strftime("%H%M%S")
    return os.path.join(
        filepath,
        '.'.join(
            (
                '_'.join(
                    (
                        time,
                        description,
                    ) if description is not None else (
                        time,
                    )
                ),
                extension
            )
        )
    )
def get_file_dialog():
    import Tkinter, tkFileDialog

    root = Tkinter.Tk()
    root.withdraw()

    return tkFileDialog.askopenfilename()
