from __future__ import annotations

from alpaca.utils import Visitor
from seer.common import Module, ContextTypes
from seer.common.params import Params
from seer.validation.nodetypes import Nodes

################################################################################
# this parses the asl and creates the module structure of the program.
class ModuleVisitor(Visitor):
    def apply(self, state: Params):
        return self._route(state.asl, state)

    @Visitor.for_asls("start")
    def start_(fn, state: Params):
        state.apply_fn_to_all_children(fn)


    @Visitor.for_asls("mod")
    def mod_(fn, state: Params) -> Module:
        node = Nodes.Mod(state)
        # create a new module; the name of the module is stored as a CLRToken
        # in the first position of the module asl.
        new_mod = Module(
            name=node.get_module_name(),
            type=ContextTypes.mod, 
            parent=state.mod)

        node.set_entered_module(new_mod)
        node.enter_module_and_apply_fn_to_child_asls(fn)

    @Visitor.for_default
    def default_(fn, state: Params):
        return