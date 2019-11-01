from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler

from src import app

def run():
    server = pywsgi.WSGIServer(('', 8080), app, handler_class=WebSocketHandler)
    server.serve_forever()

if __name__ == "__main__":
    run()
