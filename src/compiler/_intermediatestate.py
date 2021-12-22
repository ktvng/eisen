from __future__ import annotations

from compiler._context import Context
from ast import AstNode

class RecursiveDescentIntermediateState():
    def __init__(self):
        self._child_paths : list[tuple[Context, AstNode]] = []
        self.args = {}

    def add_child(self, cx : Context, node : AstNode):
        self._child_paths.append((cx, node))

    def add_arg(self, name : str, val):
        self.args[name] = val

    def get_paths(self) -> list[tuple[Context, AstNode]]:
        return self._child_paths