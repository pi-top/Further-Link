import os
import asyncio
from shutil import copy
import websockets

from .message import parse_message, create_message
from .process_handler import ProcessHandler

work_dir = os.environ.get("FURTHER_LINK_WORK_DIR", "/tmp")
lib = os.path.dirname(os.path.realpath(__file__)) + '/lib'
for file_name in os.listdir(lib):
    file = os.path.join(lib, file_name)
    if os.path.isfile(os.path.join(lib, file)):
        copy(file, work_dir)


async def app(socket, path):
    process_handler = ProcessHandler(socket, work_dir=work_dir)
    bad_message_message = create_message('error', {'message': 'Bad message'})
    print('New connection', id(socket))

    async def consu(socket):
        try:
            async for message in socket:
                try:
                    m_type, m_data = parse_message(message)

                except Exception as e:
                    if isinstance(message, str):
                        await socket.send(bad_message_message)
                    continue

                if (m_type == 'start'
                        and not process_handler.is_running()
                        and 'sourceScript' in m_data
                        and isinstance(m_data.get('sourceScript'), str)):
                    # TODO should pass the callbacks for handling output, ipc messages, stopped
                    # actually maybe better to assign them from here
                    await process_handler.start(m_data['sourceScript'])

                elif (m_type == 'stdin'
                      and process_handler.is_running()
                      and 'input' in m_data
                      and isinstance(m_data.get('input'), str)):
                    await process_handler.send_input(m_data['input'])

                elif (m_type == 'stop' and process_handler.is_running()):
                    process_handler.stop()

                else:
                    await socket.send(bad_message_message)
        finally:
            print('Closed connection', id(socket))
            process_handler.stop()

    async def cons(socket):
        try:
            async for message in socket:
                await socket.send(message)
        except Exception as e:
            print(e)

    async def prod(socket):
        i = 0
        while True:
            await asyncio.sleep(10)
            i += 1
            await socket.send('producer ' + str(i))

    await consu(socket)
    # consumer_task = asyncio.ensure_future(consu(socket))
    # producer_task = asyncio.ensure_future(
    #     prod(socket)
    # )
    # done, pending = await asyncio.wait(
    #     [consumer_task, producer_task],
    #     return_when=asyncio.FIRST_COMPLETED,
    # )
    # for task in pending:
    #     task.cancel()
