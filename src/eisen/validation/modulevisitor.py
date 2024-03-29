from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.concepts import Module
from eisen.state.basestate import BaseState as State
import eisen.adapters as adapters

class ModuleVisitor(Visitor):
    """this parses the ast and creates the module structure of the program"""

    def run(self, state: State):
        self.apply(state)
        return state

    def apply(self, state: State):
        return self._route(state.get_ast(), state)

    @Visitor.for_ast_types("start")
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_ast_types("mod")
    def mod_(fn, state: State) -> Module:
        node = adapters.Mod(state)
        node.set_entered_module(
            Module(name=node.get_module_name(), parent=state.get_enclosing_module()))

        node.enter_module_and_apply(fn)

    @Visitor.for_default
    def default_(fn, state: State):
        return
