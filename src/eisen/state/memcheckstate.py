from __future__ import annotations
from typing import TYPE_CHECKING

from alpaca.concepts import Module, Context, Type, AbstractException
from alpaca.clr import CLRList

from eisen.state.basestate import BaseState
from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor as State
from eisen.common.eiseninstance import EisenFunctionInstance
if TYPE_CHECKING:
    from eisen.memory.memcheck import CurriedFunction

class MemcheckState(State):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    def but_with(self,
            asl: CLRList = None,
            context: Context = None,
            mod: Module = None,
            depth: int = None,
            inherited_fns: list[EisenFunctionInstance] = None,
            argument_type: Type = None,
            exceptions: list = None,
            ) -> MemcheckState:

        return self._but_with(
            asl=asl,
            context=context,
            mod=mod,
            depth=depth,
            inherited_fns=inherited_fns,
            argument_type=argument_type,
            exceptions=exceptions)

    @classmethod
    def create_from_basestate(cls, state: BaseState):
        return MemcheckState(**state._get(),
                             depth=None,
                             inherited_fns={},
                             argument_type=None)

    def get_depth(self) -> int:
        return self.depth

    def get_argument_type(self) -> Type:
        return self.argument_type

    def get_inherited_fns(self) -> dict[str, CurriedFunction]:
        return self.inherited_fns
