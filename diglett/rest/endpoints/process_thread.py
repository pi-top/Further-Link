import threading
import logging
import subprocess

import time

'''
 process running some cmd and use webcoket send result back
'''

log = logging.getLogger(__name__)


class Process(threading.Thread):
    def __init__(self, cmd, websocket):
        '''
        init process
        :param cmd: command
        :param websocket: websocket object
        '''
        threading.Thread.__init__(self)
        self.cmd = cmd
        self.websocket = websocket
        self.is_stop = False

    def run(self):
        '''
        running subprocess
        :return:
        '''
        self.__run()

    def stop(self):
        '''
        stop thread and subprocess
        :return:
        '''
        self.is_stop = True
        self.join()

    def __run(self):
        self.pipe_process = subprocess.Popen(self.cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        # iterate lines and use websocket send them to frontend
        for line in iter(self.pipe_process.stdout.readline, 'b'):
            if self.is_stop:
                break
            # decode byte to str
            result = line.decode(encoding='utf-8')
            if result == '' and self.pipe_process.poll() != None:
                break

            # sending the log to client
            log.debug(result)
            if self.websocket.closed:
                break

            self.websocket.send(result)
            time.sleep(.05)

        # end of file (EOF)
        if not self.websocket.closed:
            self.websocket.send("EOF")

        # close stdout that real stop subprocess running
        self.pipe_process.stdout.close()
        # kill subprocess
        self.pipe_process.kill()
