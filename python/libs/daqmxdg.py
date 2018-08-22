from daqmx import *
import sys
import select
import socket
from time import time
from thread import start_new_thread

save_timeout = 1.0

addr = '0.0.0.0'
try:
    port = int(sys.argv[-2])
    task_name = sys.argv[-1]
except Exception:
    print '\nusage:'
    print '\npython daqmxdg.py <port> <task>'
    print '\n<port>: port that delay generator will listen on'
    print '\n<task>: name of daqmx counter output task'
    exit(1)

set_delay_command = 's'
get_delay_command = 'g'

commands = (set_delay_command,get_delay_command)

success_response = 's'
invalid_command_response = 'i'

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((addr, port))
server_socket.listen(5)

conns = []

raw_handle = c_uint32(0)
daqmx(
    dll.DAQmxLoadTask,
    (
        task_name,
        byref(raw_handle)
    )
)
handle = raw_handle.value

def parse_command(message):
    message = message.strip()
    success = True
    command = None
    data = None
    try:
        command = message[0]
        if command not in commands:
            success = False
        elif command == set_delay_command:
            data = int(message.split(' ')[-1])
            if data < 1000:
                success = False
    except Exception:
        success = False
    return (success,command,data)


def close_connection(conn):
    conn.close()
    conns.remove(conn)

def add_connection(conn):
    conns.append(conn)

def poll_connections():
    return select.select(conns,[],[],0)[0] if conns else []

def get_connections():
    r, _, _ = select.select([server_socket],[],[],0)
    if r:        
        conn, addr = server_socket.accept()
        print conn, addr
        add_connection(conn)

def get_delay():
    raw_delay = c_double(0)
    daqmx(
        dll.DAQmxGetCOPulseTimeInitialDelay,
        (
            handle,
            None,
            byref(raw_delay)
        )
    )
    return int(1E9*raw_delay.value)

def set_delay(delay):
    daqmx(
        dll.DAQmxSetCOPulseTimeInitialDelay,
        (
            handle,
            None,
            c_double(1.0E-9*delay) # in seconds
        )
    )

def task_done():
    raw_task_done = c_uint32(0)
    daqmx(
        dll.DAQmxGetTaskComplete,
        (
            handle,
            byref(raw_task_done)
        )
    )
    return bool(raw_task_done.value)

def stop_task():
    daqmx(
        dll.DAQmxStopTask,
        (
            handle,
        )            
    )

def start_task():
    daqmx(
        dll.DAQmxStartTask,
        (
            handle,
        )            
    )

def set_trigger():
    daqmx(
        dll.DAQmxCfgDigEdgeStartTrig,
        (
            handle,
            'pfi38',
            constants['DAQmx_Val_Rising']
        )
    )

def pulse_done():
    pulse_done = c_uint32(0)
    daqmx(
        dll.DAQmxGetCOPulseDone,
        (
            handle,
            None,
            byref(pulse_done)
        )
    )
    return bool(pulse_done.value)

def save_channel():
    channels = create_string_buffer(BUF_SIZE)
    daqmx(
        dll.DAQmxGetTaskChannels,
        (
            handle,
            channels,
            BUF_SIZE
        )
    )
    channel = parseStringList(channels.value)[0]
    daqmx(
        dll.DAQmxSaveGlobalChan,
        (
            handle,
            channel,
            None,
            None,
            constants['DAQmx_Val_Save_Overwrite'] |
            constants['DAQmx_Val_Save_AllowInteractiveEditing'] |
            constants['DAQmx_Val_Save_AllowInteractiveDeletion']
        )
    )
delay_requested = []
set_trigger()
start_task()
save_requested = False
save_timer = None
while True:
    if save_requested and time() - save_timer > save_timeout:
        start_new_thread(save_channel,())
        save_requested = False
    if task_done():
        stop_task()
        if delay_requested:
            set_delay(delay_requested.pop())
            save_requested = True
            save_timer = time()
        start_task()
    for conn in poll_connections():
        success, command, data = parse_command(conn.recv(64))
        if not success:
            conn.send(invalid_command_response)
        elif command == set_delay_command:
            while delay_requested: delay_requested.pop()
            delay_requested.append(data)
            conn.send(success_response)
        elif command == get_delay_command:
            delay = get_delay()
            conn.send(str(get_delay())) # in nanoseconds
        close_connection(conn)
    get_connections()
