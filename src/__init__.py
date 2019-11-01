from flask import Flask
from flask_sockets import Sockets
import json

from .process_handler import ProcessHandler

app = Flask(__name__)
sockets = Sockets(app)

@app.route('/status')
def ok():
    return 'OK'

@sockets.route('/exec')
def api(socket):
    process_handler = ProcessHandler(socket)
    bad_message_message = json.dumps({
        'type':'error',
        'data': {
            'message': 'Bad message'
        }
    })

    while True:
        try:
            # calling receive is necessary before checking if closed
            m = socket.receive()
            if (socket.closed):
                if process_handler.is_running():
                    process_handler.stop()
                break;
            message = json.loads(m)
            type = message['type']
        except Exception as e:
            socket.send(bad_message_message)
            continue

        if (type == 'start'
            and 'data' in message
            and 'sourceScript' in message['data']
            and isinstance(message.get('data').get('sourceScript'), str)):
                process_handler.start(message['data']['sourceScript'])
                socket.send(json.dumps({'type': 'started'}))

        elif (type == 'stdin'
            and process_handler.is_running()
            and 'data' in message
            and 'input' in message['data']
            and isinstance(message.get('data').get('input'), str)):
                process_handler.input(message['data']['input'])

        elif (type == 'stop'
            and process_handler.is_running()):
            process_handler.stop()

        else:
            socket.send(bad_message_message)
