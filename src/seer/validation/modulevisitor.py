from __future__ import annotations

from alpaca.utils import Visitor
from seer.common import Module, ContextTypes
from seer.common.params import Params

################################################################################
# this parses the asl and creates the module structure of the program.
class ModuleVisitor(Visitor):
    def apply(self, state: Params):
        return self._route(state.asl, state)

    # set the module inside which a given asl resides.
    def sets_module(f):
        def decorator(fn, state: Params):
            state.assign_module()
            return f(fn, state)
        return decorator

    @Visitor.for_default
    @sets_module
    def default_(fn, state: Params) -> Module:
        for child in state.get_child_asls():
            fn.apply(state.but_with(asl=child))

    @Visitor.for_asls("mod")
    @sets_module
    def mod_(fn, state: Params) -> Module:
        # create a new module; the name of the module is stored as a CLRToken
        # in the first position of the module asl.
        new_mod = Module(
            name=state.first_child().value,
            type=ContextTypes.mod, 
            parent=state.mod)

        for child in state.get_child_asls():
            fn.apply(state.but_with(
                asl=child, 
                mod=new_mod))
                