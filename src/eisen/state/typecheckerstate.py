from __future__ import annotations

from alpaca.concepts import Module, Context, Type
from alpaca.clr import CLRList

from eisen.state.basestate import BaseState

class TypeCheckerState(BaseState):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    def but_with(self,
            asl: CLRList = None,
            context: Context = None,
            mod: Module = None,
            arg_type: Type = None
            ) -> BaseState:

        return self._but_with(
            asl=asl,
            context=context,
            mod=mod,
            arg_type=arg_type)

    @classmethod
    def create_from_basestate(cls, state: BaseState):
        return TypeCheckerState(**state._get(), arg_type=None)

    def get_arg_type(self) -> Type | None:
        return self.arg_type
