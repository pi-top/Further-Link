import os
import asyncio
from aiohttp import web
import aiohttp_cors
import ssl
import codecs

from src import exep, status


def ssl_context():
    if not os.environ.get('FURTHER_LINK_NOSSL') is None:
        return
    dir = os.path.dirname(os.path.realpath(__file__))
    cert = dir + '/cert.pem'
    key = dir + '/key.pem'

    def p():
        with open(dir + '/data', 'r') as f:
            return codecs.getencoder('rot-13')(f.read()[:-1])[0]

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=cert, keyfile=key, password=p)
    return context


def run():
    port = int(os.environ.get('FURTHER_LINK_PORT', 8028))

    app = web.Application()
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })
    status_resource = cors.add(app.router.add_resource('/status'))
    cors.add(status_resource.add_route('GET', status))

    exec_resource = cors.add(app.router.add_resource('/exec'))
    cors.add(exec_resource.add_route('GET', exep))

    web.run_app(app, port=port, ssl_context=ssl_context())


if __name__ == '__main__':
    run()
