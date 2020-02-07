import os
import asyncio
import websockets

from src import app


def run(loop):
    port = int(os.environ.get('FURTHER_LINK_PORT', 8028))
    asyncio.set_event_loop(loop)
    asyncio.get_child_watcher().attach_loop(loop)
    start_server = websockets.serve(app, '', port)
    loop.run_until_complete(start_server)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    run(loop)
    loop.run_forever()
