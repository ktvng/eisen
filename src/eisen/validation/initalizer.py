from __future__ import annotations

from eisen.common.nodedata import NodeData
from alpaca.utils import Visitor
from eisen.state.basestate import BaseState

class Initializer(Visitor):
    def run(self, state: BaseState):
        self.apply(state)
        return state

    def apply(self, state: BaseState) -> None:
        return self._route(state.get_asl(), state)

    @Visitor.for_default
    def default_(fn, state: BaseState) -> None:
        state.get_asl().data = NodeData()
        for child in state.get_child_asls():
            fn.apply(state.but_with(asl=child))
