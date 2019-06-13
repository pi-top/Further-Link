# coding=utf-8
from flask import Flask
from flask_cors import CORS
from flask_sockets import Sockets

from diglett.base.log4py import logger
from diglett.base.tools.regexConverter import RegexConverter
from diglett.rest import api, api_blueprint
from diglett.rest.endpoints import process, execute
from diglett.rest.endpoints.battery import ns_battery
from diglett.rest.endpoints.beatheart import ns_beatheart
from diglett.rest.endpoints.codefile import ns_file
from diglett.rest.endpoints.execute import ns_exec
from diglett.rest.endpoints.process import ns_process

app = Flask(__name__)
sockets = Sockets(app)
# 跨域设置，允许跨域
CORS(app, supports_credentials=True, resources={r'/*': {"origins": "*"}})

app.config.from_object('settings')
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
app.url_map.converters['regex'] = RegexConverter

logger.info("配置文件路径 ====> " + app.config["PITOP_CONF"])
logger.info("缓存文件路径 ====> " + app.config["CACHEDATA_JSON"])

api.add_namespace(ns_battery)
api.add_namespace(ns_beatheart)
api.add_namespace(ns_exec)
# api.add_namespace(ns_file)
# api.add_namespace(ns_process)

app.register_blueprint(blueprint=api_blueprint)

# ws
# sockets.register_blueprint(process.ws)
sockets.register_blueprint(execute.ws)
