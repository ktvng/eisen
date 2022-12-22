from __future__ import annotations

from alpaca.utils import Visitor
from eisen.common import Module, ContextTypes
from eisen.common.params import State
from eisen.validation.nodetypes import Nodes

################################################################################
# this parses the asl and creates the module structure of the program.
class ModuleVisitor(Visitor):
    def apply(self, state: State):
        return self._route(state.asl, state)

    @Visitor.for_asls("start")
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_asls("mod")
    def mod_(fn, state: State) -> Module:
        node = Nodes.Mod(state)
        node.set_entered_module(
            Module(
                name=node.get_module_name(),
                type=ContextTypes.mod, 
                parent=state.mod))

        node.enter_module_and_apply_fn_to_child_asls(fn)

    @Visitor.for_default
    def default_(fn, state: State):
        return
    