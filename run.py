# coding=utf-8
import configparser
import logging.config

from reg_thread import RegToServer
from settings import LOGGING_CONF
from src import app

if __name__ == "__main__":
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler

    logging.config.fileConfig(LOGGING_CONF)
    log = logging.getLogger(__name__)
    log.info('>>>>> Starting server <<<<<')
    try:
        # start flask service
        cf = configparser.ConfigParser()
        cf.read(app.config['PITOP_CONF'], encoding='UTF-8')
        local_port = cf.get("sys", "local_port")
        RegToServer(local_port).start()
        log.info("The Server  port [" + local_port + "]")
        server = pywsgi.WSGIServer(('0.0.0.0', int(local_port)), app, log=log, handler_class=WebSocketHandler)
        server.serve_forever()
    except Exception as e:
        log.error("server starting failed")
