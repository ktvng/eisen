from __future__ import annotations

from alpaca.concepts import Module, Context
from alpaca.clr import CLRList

from eisen.state.stateb import StateB


class ToPythonState(StateB):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    def but_with(self,
            asl: CLRList = None,
            context: Context = None,
            mod: Module = None,
            inside_constructor: bool = None,
            ret_names: list[str] = None,
            ) -> ToPythonState:

        return self._but_with(
            asl=asl,
            context=context,
            mod=mod,
            inside_constructor=inside_constructor,
            ret_names=ret_names,)

    @classmethod
    def create_from_stateb(cls, state: StateB):
        return ToPythonState(**state._get(), ret_names=None)

    def get_ret_names(self) -> list[str] | None:
        return self.ret_names
