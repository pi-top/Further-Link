import os
import subprocess
import threading
import time

from src import logger
from src.base.command import Command

'''
 process running some cmd and use webcoket send result back
'''


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
        self.pipe = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT)

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
        self.__kill()
        self.join()

    def write(self, content):
        if self.is_alive():
            self.pipe.stdin.write(content.encode("utf-8"))
            self.pipe.stdin.flush()

    def __run(self):
        # iterate lines and use websocket send them to frontend
        for line in iter(self.pipe.stdout.readline, 'b'):
            if self.is_stop:
                break
            # decode byte to str
            result = line.decode(encoding='utf-8')
            if result == '' and self.pipe.poll() != None:
                break

            # sending the log to client
            logger.debug(result)
            if self.websocket.closed:
                break

            self.websocket.send(result)
            time.sleep(.05)

        self.__kill()

    def __kill(self):
        # kill pid
        flag = self.__grep_awk()

        if not flag:
            # close stdout that real stop subprocess running
            self.pipe.stdout.close()

            # kill subprocess
            self.pipe.kill()

        # end of file (EOF)
        if not self.websocket.closed:
            self.websocket.send(Command.EOF.value)

    def __grep_awk(self):
        """
        find the cmd thread pid
        :return:  pid
        """
        command = "ps -ef|grep '" + (
            self.cmd.replace('python3', '').replace("  ", "").replace(" ", "")) + "'|awk '{print $2}'"
        pids = os.popen(command).readlines()
        if pids:
            count = 0
            for pid in pids:
                if pid:
                    kill_pid = pid.replace('\n', '')
                    os.popen("kill -9 " + kill_pid)
                    count += 1

            if count > 0:
                return True
            else:
                return False
        else:
            return False
