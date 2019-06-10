# coding=utf-8
import configparser

from reg_nat_thread import RegNat
from support import app, logger

if __name__ == "__main__":
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler

    try:
        # 启动flask 服务
        cf = configparser.ConfigParser()
        cf.read(app.config['PITOP_CONF'])
        local_port = cf.get("sys", "local_port")
        # RegNat(local_port).start()
        logger.info("start flask,the port:" + local_port)
        server = pywsgi.WSGIServer(('0.0.0.0', int(local_port)), app, handler_class=WebSocketHandler)
        server.serve_forever()
    except Exception as e:
        logger.error("reg to server failed")
