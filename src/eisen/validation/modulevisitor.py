from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.concepts import Module
from eisen.common.state import State
from eisen.validation.nodetypes import Nodes

class ModuleVisitor(Visitor):
    """this parses the asl and creates the module structure of the program"""
    def apply(self, state: State):
        return self._route(state.get_asl(), state)

    @Visitor.for_asls("start")
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_asls("mod")
    def mod_(fn, state: State) -> Module:
        node = Nodes.Mod(state)
        node.set_entered_module(
            Module(name=node.get_module_name(), parent=state.get_enclosing_module()))

        node.enter_module_and_apply(fn)

    @Visitor.for_default
    def default_(fn, state: State):
        return
