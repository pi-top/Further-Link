# coding=utf-8
"""
配置上下文 文件
注意配置文件变量必须大写否则错误
"""
import os

_basedir = os.path.abspath(os.path.dirname(__file__))

# pitop 配置文件
PITOP_CONF = os.path.join(_basedir, 'pitop.conf')

# cachedata 缓存文件
CACHEDATA_JSON = os.path.join(_basedir, 'cachedata.json')

FRP_INI = os.path.join(_basedir, 'frp.ini')

# Flask settings
FLASK_DEBUG = True  # Do not use debug mode in production

# Flask-Restplus settings
SWAGGER_UI_DOC_EXPANSION = 'list'
RESTPLUS_VALIDATE = True
RESTPLUS_MASK_SWAGGER = False
ERROR_404_HELP = False

del os
