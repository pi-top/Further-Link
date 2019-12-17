from gevent import monkey
monkey.patch_all()  # noqa

import os
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from src import app


dir = os.path.dirname(os.path.realpath(__file__))


def run():
    port = int(os.environ.get("FURTHER_LINK_PORT", 8028))
    ssl_args = {
        'keyfile': dir + '/key.pem',
        'certfile': dir + '/cert.pem',
    }
    server = pywsgi.WSGIServer(('', port), app, handler_class=WebSocketHandler, **ssl_args)
    server.serve_forever()


if __name__ == "__main__":
    run()
