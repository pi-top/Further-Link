import logging

from flask import Blueprint
from flask_restplus import Api

import settings

log = logging.getLogger(__name__)

api_blueprint = Blueprint('api', __name__, url_prefix='/api')

api = Api(
    app=api_blueprint,
    version='1.0.0',
    title='Remote,Local WebIde Deglett API',
    description='''this is for deglett apis show how to use apis''',
    contact='@pi-top.com',
    contact_url='https://www.pi-top.com',
    contact_email="leo@pi-top.com"
)


@api.errorhandler
def default_error_handler(e):
    message = 'An unhandled exception occurred.'
    log.exception(message)

    if not settings.FLASK_DEBUG:
        return {'message': message}, 500
