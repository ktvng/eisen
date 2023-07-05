from __future__ import annotations

from alpaca.concepts import Module, Context
from alpaca.clr import AST

from eisen.state.basestate import BaseState
from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor as State

class ToPythonState(State):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    def but_with(self,
            ast: AST = None,
            context: Context = None,
            mod: Module = None,
            ret_names: list[str] = None,
            ) -> ToPythonState:

        return self._but_with(
            ast=ast,
            context=context,
            mod=mod,
            ret_names=ret_names,)

    @classmethod
    def create_from_basestate(cls, state: BaseState):
        return ToPythonState(**state._get(), ret_names=None)

    def get_ret_names(self) -> list[str] | None:
        return self.ret_names
