# coding=utf-8
from flask import Flask
from flask_sockets import Sockets
from flask_cors import CORS

from support.base.log4py import logger
from support.base.tools.regexConverter import RegexConverter

app = Flask(__name__)
sockets = Sockets(app)
# 跨域设置，允许跨域
CORS(app, supports_credentials=True, resources={r'/*': {"origins": "*"}})

app.config.from_object('pitopminderconfig')
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
app.url_map.converters['regex'] = RegexConverter

logger.info("配置文件路径 ====> " + app.config["PITOP_CONF"])
logger.info("缓存文件路径 ====> " + app.config["CACHEDATA_JSON"])

from support.views import beatheartctrl, batteryctrl, osoptctrl, processctrl

# http
app.register_blueprint(processctrl.pitop)
app.register_blueprint(beatheartctrl.pitop)
app.register_blueprint(batteryctrl.pitop)
app.register_blueprint(osoptctrl.pitop)

# ws
sockets.register_blueprint(processctrl.ws)
sockets.register_blueprint(batteryctrl.ws)
