from __future__ import annotations

from alpaca.compiler._context import Context
from alpaca.asts import ASTNode

class RecursiveDescentIntermediateState():
    def __init__(self):
        self._child_paths : list[tuple[Context, ASTNode]] = []
        self.args = {}

    def add_child(self, cx : Context, node : ASTNode):
        self._child_paths.append((cx, node))

    def add_arg(self, name : str, val):
        self.args[name] = val

    def get_paths(self) -> list[tuple[Context, ASTNode]]:
        return self._child_paths