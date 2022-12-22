from __future__ import annotations

from eisen.common.nodedata import NodeData
from alpaca.utils import Visitor
from eisen.common.params import State

class Initializer(Visitor):
    def apply(self, state: State) -> None:
        return self._route(state.asl, state)

    @Visitor.for_default
    def default_(fn, state: State) -> None:
        state.asl.data = NodeData()
        for child in state.get_child_asls():
            fn.apply(state.but_with(asl=child))
        