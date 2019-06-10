# coding=utf-8
'''
this class will be create a tree object for init project from further
'''


class TreeVO:
    def __init__(self):
        self.id = None
        self.title = None
        self.path = None
        self.key = None
        self.isLeaf = False
        self.children = None
        self.file_path = None

    @property
    def is_leaf(self):
        return self.isLeaf

    @is_leaf.setter
    def is_leaf(self, is_leaf):
        self.isLeaf = is_leaf
