from __future__ import annotations

from alpaca.concepts import Module, Context, Type
from alpaca.clr import CLRList

from eisen.common.restriction import GeneralRestriction
from eisen.state.basestate import BaseState

class StateA(BaseState):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    def but_with(self,
            asl: CLRList = None,
            context: Context = None,
            mod: Module = None,
            inside_constructor: bool = None,
            ) -> StateA:

        return self._but_with(
            asl=asl,
            context=context,
            mod=mod,
            inside_constructor=inside_constructor)

    @classmethod
    def create_from_basestate(cls, state: BaseState):
        return StateA(**state._get())

    def get_returned_type(self) -> Type:
        """canonical way to access the type returned from this node"""
        return self.get_node_data().returned_type

    def get_restriction(self) -> GeneralRestriction:
        return self.get_returned_type().get_restrictions()[0]
