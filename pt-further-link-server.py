import os
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler

from src import app


def run():
    port = int(os.environ.get("FURTHER_LINK_PORT", 8028))
    server = pywsgi.WSGIServer(('', port), app, handler_class=WebSocketHandler)
    server.serve_forever()


if __name__ == "__main__":
    run()
