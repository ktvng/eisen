from __future__ import annotations

from alpaca.concepts import Module
from eisen.adapters.nodeinterface import AbstractNodeInterface

class Mod(AbstractNodeInterface):
    asl_type = "mod"
    examples = """
    (mod name ...)
    """
    get_module_name = AbstractNodeInterface.get_name_from_first_child
    def get_entered_module(self) -> Module:
        return self.state.get_node_data().enters_module

    def set_entered_module(self, mod: Module):
        self.state.get_node_data().enters_module = mod

    def enter_module_and_apply(self, fn):
        for child in self.state.get_asl()[1:]:
            fn.apply(self.state.but_with(
                asl=child,
                mod=self.get_entered_module()))

    def enter_module_and_apply_with_return(self, fn):
        lst = []
        for child in self.state.get_asl()[1:]:
            lst.append(fn.apply(self.state.but_with(
                asl=child,
                mod=self.get_entered_module())))
        return lst
