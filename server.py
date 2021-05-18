#!/usr/bin/python3

import os
import ssl
import codecs

from aiohttp import web
import aiohttp_cors

from src import status, version, apt_version, run_py


def port():
    return int(os.environ.get('FURTHER_LINK_PORT', 8028))


def ssl_context():
    # use ssl if FURTHER_LINK_NOSSL is unset, 0 or false
    if os.environ.get('FURTHER_LINK_NOSSL', '0').lower() not in ['0', 'false']:
        return None

    file_dir = os.path.dirname(os.path.realpath(__file__))
    cert = file_dir + '/cert.pem'
    key = file_dir + '/key.pem'

    def password():
        with open(file_dir + '/data', 'r') as file:
            return codecs.getencoder('rot-13')(file.read()[:-1])[0]

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=cert, keyfile=key, password=password)
    return context


def create_app():
    app = web.Application()
    cors = aiohttp_cors.setup(app, defaults={
        '*': aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers='*',
            allow_headers='*',
        )
    })
    status_resource = cors.add(app.router.add_resource('/status'))
    cors.add(status_resource.add_route('GET', status))

    status_resource = cors.add(app.router.add_resource('/version/apt/{pkg}'))
    cors.add(status_resource.add_route('GET', apt_version))

    status_resource = cors.add(app.router.add_resource('/version'))
    cors.add(status_resource.add_route('GET', version))

    exec_resource = cors.add(app.router.add_resource('/run-py'))
    cors.add(exec_resource.add_route('GET', run_py))

    return app


async def run_async():
    runner = web.AppRunner(create_app())
    await runner.setup()
    site = web.TCPSite(runner, port=port(), ssl_context=ssl_context())
    await site.start()
    return runner


def run():
    return web.run_app(
        create_app(),
        port=port(),
        ssl_context=ssl_context(),
        # Web sockets are open indefinitely
        # So don't ignore sigterm, as it may cause shutdown to hang/slow down
        # unnecessary. Pi isn't serving fast-responding HTTP requests.
        handle_signals=False
    )


if __name__ == '__main__':
    run()
