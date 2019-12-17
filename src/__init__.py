import os
from flask import Flask
from flask_sockets import Sockets
from flask_cors import CORS
from shutil import copy

from .message import parse_message, create_message
from .process_handler import ProcessHandler

app = Flask(__name__)
CORS(app)
sockets = Sockets(app)

work_dir = '/tmp'
lib = os.path.dirname(os.path.realpath(__file__)) + '/lib'
for file_name in os.listdir(lib):
    file = os.path.join(lib, file_name)
    if os.path.isfile(os.path.join(lib, file)):
        copy(file, work_dir)


@app.route('/status')
def ok():
    return 'OK'


@sockets.route('/exec')
def api(socket):
    process_handler = ProcessHandler(socket, work_dir=work_dir)
    bad_message_message = create_message('error', {'message': 'Bad message'})
    print('New connection', id(socket))

    while not socket.closed:
        try:
            message = socket.receive()
            m_type, m_data = parse_message(message)

        except Exception as e:
            if isinstance(message, str):
                socket.send(bad_message_message)
            continue

        if (m_type == 'start'
            and not process_handler.is_running()
            and 'sourceScript' in m_data
                and isinstance(m_data.get('sourceScript'), str)):
            process_handler.start(m_data['sourceScript'])
            socket.send(create_message('started'))

        elif (m_type == 'stdin'
              and process_handler.is_running()
              and 'input' in m_data
              and isinstance(m_data.get('input'), str)):
            process_handler.send_input(m_data['input'])

        elif (m_type == 'stop' and process_handler.is_running()):
            process_handler.stop()

        else:
            socket.send(bad_message_message)

    print('Closed connection', id(socket))
    process_handler.stop()
