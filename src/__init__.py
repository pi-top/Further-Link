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
    proccess_handler = ProcessHandler(socket)
    bad_message_message = json.dumps({
        "type":"error",
        "data": {
            "message": "Bad message"
        }
    })

    while True:
        try:
            m = socket.receive()
            message = json.loads(m)
            type = message['type']
        except Exception as e:
            socket.send(bad_message_message)
            continue

        if (type == 'start'
            and 'data' in message
            and 'sourceScript' in message['data']
            and isinstance(message.get('data').get('sourceScript'), str)):
                proccess_handler.start(message['data']['sourceScript'])
                socket.send('{"type":"started"}')

        elif (type == 'stdin'
            and 'data' in message
            and 'input' in message['data']
            and isinstance(message.get('data').get('input'), str)):
                proccess_handler.input(message['data']['input'])

        elif type == 'stop':
            proccess_handler.stop()

        else:
            socket.send(bad_message_message)
