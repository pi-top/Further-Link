from gevent import monkey
monkey.patch_all()  # noqa

import os
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
import ssl
import codecs
from src import app


dir = os.path.dirname(os.path.realpath(__file__))

cert = dir + '/cert.pem'
key = dir + '/key.pem'


def p():
    with open(dir + '/data', 'r') as f:
        return codecs.getencoder('rot-13')(f.read()[:-1])[0]


context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.load_cert_chain(certfile=cert, keyfile=key, password=p)


def run():
    port = int(os.environ.get('FURTHER_LINK_PORT', 8028))
    server = pywsgi.WSGIServer(('', port), app, handler_class=WebSocketHandler, ssl_context=context)
    server.serve_forever()


if __name__ == '__main__':
    run()
