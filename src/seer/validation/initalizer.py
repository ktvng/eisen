from __future__ import annotations

from seer.common.nodedata import NodeData
from alpaca.utils import Visitor
from seer.common.params import Params

class Initializer(Visitor):
    def apply(self, state: Params) -> None:
        return self._route(state.asl, state)

    @Visitor.for_default
    def default_(fn, state: Params) -> None:
        state.asl.data = NodeData()
        for child in state.get_child_asls():
            fn.apply(state.but_with(asl=child))
        