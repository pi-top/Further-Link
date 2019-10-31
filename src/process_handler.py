import subprocess
import json
import threading

class ProcessHandler:
    def __init__(self, socket):
        self.socket = socket

    def start(self, script):
        command = 'python -c "' + script + '"'
        self.process = subprocess.Popen(command, shell=True,
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT)

        self.handler = threading.Thread(target=self.handle_process, daemon=True)
        self.handler.start()


    def handle_process(self):
        for line in iter(self.process.stdout.readline, 'b'):
            # decode byte to str
            output = line.decode(encoding='utf-8')
            stopped = self.process.poll() != None
            if output == '' and stopped:
                break

            # sending the log to client
            self.socket.send(json.dumps({
                'type': 'stdout',
                'data': {
                    'output': output
                }
            }))

        self.socket.send(json.dumps({ "type": "stopped" }))
