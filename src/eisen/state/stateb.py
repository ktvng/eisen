from __future__ import annotations

from alpaca.concepts import Module, Context
from alpaca.clr import CLRList

from eisen.common.eiseninstance import EisenInstance
from eisen.state.statea import StateA

class StateB(StateA):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    def but_with(self,
            asl: CLRList = None,
            context: Context = None,
            mod: Module = None,
            inside_constructor: bool = None,
            ) -> StateB:

        return self._but_with(
            asl=asl,
            context=context,
            mod=mod,
            inside_constructor=inside_constructor)

    @classmethod
    def create_from_state_a(cls, state: StateA):
        return StateB(**state._get())

    def get_instances(self) -> list[EisenInstance]:
        """canonical way to get instances stored in this node"""
        return self.get_node_data().instances
