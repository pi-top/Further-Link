from flask_restplus import fields

from diglett.rest import api

code_vo = api.model('code vo object', {
    'id': fields.String(required=True, description='the code block id'),
    'path': fields.String(required=True, description='the code path and name'),
    'content': fields.String(required=True, description='the code'),
    'projectVersionId': fields.String(required=True, description='the cod own which project id')
})

code_vo_list = api.inherit('code vo list', {
    'code_vos': fields.List(fields.Nested(code_vo))
})
