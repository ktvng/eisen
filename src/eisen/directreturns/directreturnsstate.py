from __future__ import annotations

from alpaca.concepts import Module, Context, Type, AbstractException
from alpaca.clr import AST, ASTToken

from eisen.state.basestate import BaseState
from eisen.typecheck.typeparser import TypeParser

class DirectReturnsState(BaseState):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    def but_with(self,
            ast: AST = None,
            context: Context = None,
            mod: Module = None,
            rets: [ASTToken] = []
            ) -> BaseState:

        return self._but_with(
            ast=ast,
            context=context,
            mod=mod,
            rets=rets,
            )

    @classmethod
    def create_from_basestate(cls, state: BaseState):
        return DirectReturnsState(**state._get(), rets=[])

    def get_rets(self) -> [ASTToken]:
        return self.rets
