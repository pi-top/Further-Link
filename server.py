import os
import asyncio
import websockets
import ssl
import codecs

from src import app


def ssl_context():
    dir = os.path.dirname(os.path.realpath(__file__))
    cert = dir + '/cert.pem'
    key = dir + '/key.pem'

    def p():
        with open(dir + '/data', 'r') as f:
            return codecs.getencoder('rot-13')(f.read()[:-1])[0]

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=cert, keyfile=key, password=p)
    return context


def run(loop):
    port = int(os.environ.get('FURTHER_LINK_PORT', 8028))
    asyncio.set_event_loop(loop)
    asyncio.get_child_watcher().attach_loop(loop)
    start_server = websockets.serve(app, '', port, ssl=ssl_context())
    loop.run_until_complete(start_server)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    run(loop)
    loop.run_forever()
