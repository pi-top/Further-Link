# coding=utf-8
'''
this VO entity will create when init project from further
'''


class CodeVO:
    def __init__(self, id=None, path=None, content='', project_version_id=None):
        self.id = id
        self.path = path
        self.content = content
        self.projectVersionId = project_version_id
