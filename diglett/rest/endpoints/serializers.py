from flask_restplus import fields

from diglett.rest import api


exec_code = api.model('code for running', {
    'path': fields.String(required=True, description='the code path and name'),
    'content': fields.String(required=True, description='the code')
})

code_vo = api.model('code vo object', {
    'id': fields.String(required=True, description='the code block id'),
    'path': fields.String(required=True, description='the code path and name'),
    'content': fields.String(required=True, description='the code'),
    'projectVersionId': fields.String(required=True, description='the cod own which project id')
})

code_vo_list = api.inherit('code vo list', {
    'code_vos': fields.List(fields.Nested(code_vo))
})


class Item(fields.Raw):
    def format(self, value):
        return value


bean = api.model('bean is response result', {
    'success': fields.Boolean(description=''),
    'info': fields.String(description=''),
    'code': fields.String(description=''),
    'data': Item()
})
