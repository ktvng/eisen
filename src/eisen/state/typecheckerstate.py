from __future__ import annotations

from alpaca.concepts import Module, Context, Type
from alpaca.clr import AST

from eisen.state.basestate import BaseState

class TypeCheckerState(BaseState):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    def but_with(self,
            ast: AST = None,
            context: Context = None,
            mod: Module = None,
            arg_type: Type = None
            ) -> BaseState:

        return self._but_with(
            ast=ast,
            context=context,
            mod=mod,
            arg_type=arg_type)

    @classmethod
    def create_from_basestate(cls, state: BaseState):
        return TypeCheckerState(**state._get(), arg_type=None)

    def get_arg_type(self) -> Type | None:
        return self.arg_type
