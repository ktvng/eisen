from __future__ import annotations

from eisen.common.nodedata import NodeData
from alpaca.utils import Visitor
from eisen.state.basestate import BaseState as State

class Initializer(Visitor):
    def run(self, state: State):
        self.apply(state)
        return state

    def apply(self, state: State) -> None:
        return self._route(state.get_ast(), state)

    @Visitor.for_tokens
    def tokens_(fn, state: State) -> None:
        state.get_ast().data = NodeData()

    @Visitor.for_default
    def default_(fn, state: State) -> None:
        state.get_ast().data = NodeData()
        for child in state.get_all_children():
            fn.apply(state.but_with(ast=child))
