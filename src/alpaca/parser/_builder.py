from __future__ import annotations
from alpaca.utils._visitor import PartialTransform, Visitor

class Builder(Visitor):
    @classmethod
    def for_procedure(cls, matching_name: str):
        def decorator(f):
            predicate = lambda n: n == matching_name
            return PartialTransform(predicate, f)
        return decorator 

    def apply(self, type_name: str, config, components: list[ASTNode | list[ASTNode]], *args):
        return self._apply(
            match_args=[type_name],
            fn_args=[config, components, *args])

    class Params:
        def __init__(self, components : list[ASTNode | list[ASTNode]]):
            self.components = components

        def but_with(self, *args, **kwargs):
            pass