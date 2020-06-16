from distutils.core import setup
setup(
    name='sitzlabrad',
    version='1.0',
    py_modules=[
        'filecreation', 
        'serialtransceiver',
        'delaygenerator',
        'steppermotor',
        'connectionmanager',
        'daqmxdg'
    ],
    packages=[
        'qtutils',
        'daqmx'
    ]
)
