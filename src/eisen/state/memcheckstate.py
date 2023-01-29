from __future__ import annotations

from alpaca.concepts import Module, Context, Type
from alpaca.clr import CLRList

from eisen.state.stateb import StateB
from eisen.common.eiseninstance import EisenFunctionInstance

class MemcheckState(StateB):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    def but_with(self,
            asl: CLRList = None,
            context: Context = None,
            mod: Module = None,
            inside_constructor: bool = None,
            depth: int = None,
            inherited_fns: list[EisenFunctionInstance] = None,
            argument_type: Type = None,
            ) -> MemcheckState:

        return self._but_with(
            asl=asl,
            context=context,
            mod=mod,
            inside_constructor=inside_constructor,
            depth=depth,
            inherited_fns=inherited_fns,
            argument_type=argument_type)

    @classmethod
    def create_from_state_b(cls, state: StateB):
        return MemcheckState(**state._get(),
                             depth=None,
                             inherited_fns=[],
                             argument_type=None)

    def get_depth(self) -> int:
        return self.depth

    def but_with_first_child(self) -> MemcheckState:
        return self.but_with(asl=self.first_child())

    def but_with_second_child(self) -> MemcheckState:
        return self.but_with(asl=self.second_child())

    def get_argument_type(self) -> Type:
        return self.argument_type
