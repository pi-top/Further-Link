import subprocess
import threading
import os
from time import sleep
from functools import partial
import socket

from .message import create_message


class ProcessHandler:
    def __init__(self, websocket):
        self.socket = websocket

    def start(self, script):
        filename = self.get_filename()
        open(filename, 'w+').write(script)

        ipc_filename = self.get_ipc_filename()
        if os.path.exists(ipc_filename):
            os.remove(ipc_filename)
        self.ipc = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.ipc.bind(ipc_filename)
        threading.Thread(target=self.handle_ipc, daemon=True).start()

        command = 'python3 -u ' + filename
        self.process = subprocess.Popen(command, shell=True,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)

        handle_stdout = partial(self.handle_output, stream='stdout')
        handle_stderr = partial(self.handle_output, stream='stderr')

        threading.Thread(target=handle_stdout, daemon=True).start()
        threading.Thread(target=handle_stderr, daemon=True).start()
        threading.Thread(target=self.handle_stopped, daemon=True).start()

    def stop(self):
        if self.is_running():
            self.process.kill()

    def clean_up(self):
        try:
            os.remove(self.get_filename())
            os.remove(self.get_ipc_filename())
        except:
            pass
        self.stop()

    def get_id(self):
        return str(id(self.socket))

    def get_filename(self):
        return '/tmp/' + self.get_id() + '.py'

    def get_ipc_filename(self):
        return '/tmp/' + self.get_id() + '.sock'

    def is_running(self):
        return hasattr(self, 'process') and self.process.poll() is None

    def send_input(self, content):
        self.process.stdin.write(content.encode('utf-8'))
        self.process.stdin.flush()

    def handle_stopped(self):
        while True:
            sleep(0.1)
            if not self.is_running():
                self.socket.send(create_message('stopped', {
                    'exitCode': self.process.returncode
                }))
                self.clean_up()
                break

    def handle_output(self, stream):
        for line in iter(getattr(self.process, stream).readline, 'b'):
            output = line.decode(encoding='utf-8')

            if output != '':
                self.socket.send(create_message(stream, {
                    'output': output
                }))

            if not self.is_running():
                break

    def handle_ipc(self):
        self.ipc.listen(1)
        while True:
            try:
                conn, addr = self.ipc.accept()
                frame = ''
                while True:
                    data = conn.recv(1024)
                    if data:
                        tokens = data.decode("utf-8").strip().split()
                        if tokens[0] == 'furtherVideo':
                            if len(frame) > 0:
                                self.socket.send(create_message('video', {
                                    'frame': frame
                                }))
                                frame = ''
                        frame += tokens[0]
            finally:
                conn.close()
