from flask import Flask
from flask_sockets import Sockets

# import execute

app = Flask(__name__)

@app.route('/status')
def ok():
    return 'OK'

# sockets = Sockets(app)
# sockets.register_blueprint(execute.ws)
