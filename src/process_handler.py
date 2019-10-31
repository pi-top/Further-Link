import subprocess
import json
import threading
from time import sleep

class ProcessHandler:
    def __init__(self, socket):
        self.socket = socket

    def start(self, script):
        command = 'python -c "' + script + '"'
        self.process = subprocess.Popen(command, shell=True,
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)

        threading.Thread(target=self.handle_stdout, daemon=True).start()
        threading.Thread(target=self.handle_stderr, daemon=True).start()
        threading.Thread(target=self.handle_stopped, daemon=True).start()

    def stop(self):
        self.process.kill()

    def handle_stdout(self):
        for line in iter(self.process.stdout.readline, 'b'):
            # decode byte to str
            output = line.decode(encoding='utf-8')
            stopped = self.process.poll() != None
            if output == '' and stopped:
                break

            # sending the log to client
            if output != '':
                self.socket.send(json.dumps({
                    'type': 'stdout',
                    'data': {
                        'output': output
                    }
                }))

    def handle_stderr(self):
        for line in iter(self.process.stderr.readline, 'b'):
            # decode byte to str
            output = line.decode(encoding='utf-8')
            stopped = self.process.poll() != None
            if output == '' and stopped:
                break

            # sending the log to client
            if output != '':
                self.socket.send(json.dumps({
                    'type': 'stderr',
                    'data': {
                        'output': output
                    }
                }))


    def handle_stopped(self):
        while True:
            sleep(0.1)
            stopped = self.process.poll() != None
            if stopped:
                self.socket.send(json.dumps({
                    "type": "stopped",
                    "data": {
                        "exitCode": self.process.returncode
                    }
                }))
                break
