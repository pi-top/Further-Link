from flask import Flask
from flask_sockets import Sockets

from .message import parse_message, create_message
from .process_handler import ProcessHandler

app = Flask(__name__)
sockets = Sockets(app)

@app.route('/status')
def ok():
    return 'OK'

@sockets.route('/exec')
def api(socket):
    process_handler = ProcessHandler(socket)
    bad_message_message = create_message('error', { 'message': 'Bad message' })

    while True:
        try:
            # calling receive is necessary before checking if closed
            message = socket.receive()
            print(message)
            if (socket.closed):
                if process_handler.is_running():
                    process_handler.stop()
                break;

            m_type, m_data = parse_message(message)

        except Exception as e:
            if isinstance(message, str):
                socket.send(bad_message_message)
            continue

        if (m_type == 'start'
            and not process_handler.is_running() # TODO this should be tested in outofordercommands
            and 'sourceScript' in m_data
            and isinstance(m_data.get('sourceScript'), str)):
                process_handler.start(m_data['sourceScript'])
                socket.send(create_message('started'))

        elif (m_type == 'stdin'
            and process_handler.is_running()
            and 'input' in m_data
            and isinstance(m_data.get('input'), str)):
                process_handler.input(m_data['input'])

        elif (m_type == 'stop' and process_handler.is_running()):
            process_handler.stop()

        else:
            socket.send(bad_message_message)
