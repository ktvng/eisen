from __future__ import annotations
from alpaca.asts import ASTNode

class AbstractBuilder():
    build_map = {}

    @classmethod
    def build_procedure(cls, build_map, name):
        def _decorator(f):
            build_map[name] = f
            return f

        return _decorator
        
    pass

    @classmethod
    def postprocess(cls, node : ASTNode) -> None:
        return

