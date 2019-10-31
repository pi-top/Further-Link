from flask import Flask
from flask_sockets import Sockets
import json
# import execute

app = Flask(__name__)
sockets = Sockets(app)

@app.route('/status')
def ok():
    return 'OK'

@sockets.route('/exec')
def api(socket):
    while True:
        try:
            message = json.loads(socket.receive())
        except Exception:
            socket.send(json.dumps( {"type":"error"} ))

        if message['type'] == 'start':
            socket.send('{"type":"started"}')

            if message['data']:
                socket.send(json.dumps({ "type" : "stdout", "data" : {"output":"hi"}}))
