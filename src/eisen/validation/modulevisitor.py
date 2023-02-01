from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.concepts import Module
from eisen.state.basestate import BaseState
import eisen.adapters as adapters

class ModuleVisitor(Visitor):
    """this parses the asl and creates the module structure of the program"""

    def run(self, state: BaseState):
        self.apply(state)
        return state

    def apply(self, state: BaseState):
        return self._route(state.get_asl(), state)

    @Visitor.for_asls("start")
    def start_(fn, state: BaseState):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_asls("mod")
    def mod_(fn, state: BaseState) -> Module:
        node = adapters.Mod(state)
        node.set_entered_module(
            Module(name=node.get_module_name(), parent=state.get_enclosing_module()))

        node.enter_module_and_apply(fn)

    @Visitor.for_default
    def default_(fn, state: BaseState):
        return
