import subprocess
from threading import Thread
import os
from time import sleep
from functools import partial
import socket

from .message import create_message

ipc_channel_names = ['video']


class ProcessHandler:
    def __init__(self, websocket, work_dir="/tmp"):
        self.websocket = websocket
        self.work_dir = work_dir
        self.id = str(id(self.websocket))

    def __del__(self):
        self.stop()

    def start(self, script):
        print('Starting', self.id)
        main_filename = self.get_main_filename()
        open(main_filename, 'w+').write(script)

        command = 'python3 -u ' + main_filename
        self.process = subprocess.Popen(command, shell=True,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)

        self.ipc_channels = {}
        for name in ipc_channel_names:
            ipc_filename = self.get_ipc_filename(name)
            if os.path.exists(ipc_filename):
                os.remove(ipc_filename)
            self.ipc_channels[name] = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.ipc_channels[name].bind(ipc_filename)
            self.ipc_channels[name].setblocking(0)

            handle_ipc = partial(self.handle_ipc, channel=name)
            Thread(target=handle_ipc, daemon=True).start()

        handle_stdout = partial(self.handle_output, stream='stdout')
        handle_stderr = partial(self.handle_output, stream='stderr')

        Thread(target=handle_stdout, daemon=True).start()
        Thread(target=handle_stderr, daemon=True).start()
        Thread(target=self.handle_stopped, daemon=True).start()

    def stop(self):
        if self.is_running():
            self.process.kill()
        self.clean_up()

    def clean_up(self):
        try:
            os.remove(self.get_main_filename())
            for name in ipc_channel_names:
                try:
                    os.remove(self.get_ipc_filename(name))
                except:
                    pass
        except:
            pass

    def get_main_filename(self):
        return self.work_dir + '/' + self.id + '.py'

    def get_ipc_filename(self, channel):
        return self.work_dir + '/' + self.id + '.' + channel + '.sock'

    def is_running(self):
        return hasattr(self, 'process') and self.process.poll() is None

    def send_input(self, content):
        self.process.stdin.write(content.encode('utf-8'))
        self.process.stdin.flush()

    def handle_stopped(self):
        while True:
            sleep(0.1)
            if not self.is_running():
                try:
                    self.websocket.send(create_message('stopped', {
                        'exitCode': self.process.returncode
                    }))
                except:
                    pass
                self.clean_up()
                print('Stopped', self.id)
                break

    def handle_output(self, stream):
        for line in iter(getattr(self.process, stream).readline, b''):
            output = line.decode(encoding='utf-8')

            if output != '':
                self.websocket.send(create_message(stream, {
                    'output': output
                }))

            if not self.is_running():
                break

    def handle_ipc(self, channel):
        self.ipc_channels[channel].listen(1)
        while True:
            if not self.is_running():
                break
            try:
                conn, addr = self.ipc_channels[channel].accept()
                message = ''
                while True:
                    if not self.is_running():
                        break
                    try:
                        data = conn.recv(4096)
                        if data:
                            tokens = data.decode("utf-8").strip().split()
                            if tokens[0] == channel:
                                if len(message) > 0:
                                    self.websocket.send(create_message(channel, {
                                        'message': message
                                    }))
                                    message = ''
                                message += tokens[1]
                            else:
                                message += tokens[0]
                    except:
                        sleep(0.001)
                        continue
                conn.close()
            except:
                sleep(0.1)
                continue
