from __future__ import annotations

from alpaca.concepts import Module, Context
from alpaca.clr import CLRList

from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor as State

class AstInterpreterState(State):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    def but_with(self,
            asl: CLRList = None,
            context: Context = None,
            mod: Module = None,
            objs: dict = None
            ) -> AstInterpreterState:

        return self._but_with(
            asl=asl,
            context=context,
            mod=mod,
            objs=objs)

    @classmethod
    def create_from_state_b(cls, state: State):
        return AstInterpreterState(**state._get(), objs={})

    def get_depth(self) -> int:
        return self.depth
