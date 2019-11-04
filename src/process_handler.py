import subprocess
import threading
from time import sleep

from .message import create_message

class ProcessHandler:
    def __init__(self, socket):
        self.socket = socket

    def start(self, script):
        filename = '/tmp/' + str(id(self.socket)) + '.py'
        open(filename, 'w+').write(script)
        # TODO clean up the file
        command = 'python3 -u ' + filename
        self.process = subprocess.Popen(command, shell=True,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)

        threading.Thread(target=self.handle_stdout, daemon=True).start()
        threading.Thread(target=self.handle_stderr, daemon=True).start()
        threading.Thread(target=self.handle_stopped, daemon=True).start()

    def stop(self):
        self.process.kill()

    def input(self, input):
        self.process.stdin.write(input.encode('utf-8'))
        self.process.stdin.flush()

    def is_running(self):
        return hasattr(self, 'process') and self.process.poll() is None

    def handle_stdout(self):
        for line in iter(self.process.stdout.readline, 'b'):
            # decode byte to str
            output = line.decode(encoding='utf-8')
            if not self.is_running():
                break

            # sending the log to client
            if output != '':
                self.socket.send(create_message('stdout', {
                    'output': output
                }))

    def handle_stderr(self):
        for line in iter(self.process.stderr.readline, 'b'):
            # decode byte to str
            output = line.decode(encoding='utf-8')
            if not self.is_running():
                break

            # sending the log to client
            if output != '':
                self.socket.send(create_message('stderr', {
                    'output': output
                }))

    def handle_stopped(self):
        while True:
            sleep(0.1)
            if not self.is_running():
                self.socket.send(create_message('stopped', {
                    'exitCode': self.process.returncode
                }))
                break
