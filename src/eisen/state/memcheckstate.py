from __future__ import annotations

from alpaca.concepts import Module, Context
from alpaca.clr import CLRList

from eisen.state.stateb import StateB

class MemcheckState(StateB):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    def but_with(self,
            asl: CLRList = None,
            context: Context = None,
            mod: Module = None,
            inside_constructor: bool = None,
            depth: int = None
            ) -> MemcheckState:

        return self._but_with(
            asl=asl,
            context=context,
            mod=mod,
            inside_constructor=inside_constructor,
            depth=depth)

    @classmethod
    def create_from_state_b(cls, state: StateB):
        return MemcheckState(**state._get(), depth=None)

    def get_depth(self) -> int:
        return self.depth
