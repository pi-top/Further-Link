from flask import Flask
from flask_sockets import Sockets

# import execute

app = Flask(__name__)
sockets = Sockets(app)

@app.route('/status')
def ok():
    return 'OK'

@sockets.route('/exec')
def api(socket):
    while True:
        message = socket.receive()
        print(message)
        socket.send(message)
