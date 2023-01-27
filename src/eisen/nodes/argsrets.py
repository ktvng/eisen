from __future__ import annotations

from alpaca.concepts import Type
from eisen.nodes.nodeinterface import AbstractNodeInterface
from eisen.common.restriction import VarRestriction

from eisen.nodes._decls import Decl

class ArgsRets(AbstractNodeInterface):
    asl_types = ["rets", "args"]
    examples = """
    (rets (: ...))
    (rets (prod_type ...))
    """

    def get_names(self) -> list[str]:
        if self.state.asl.has_no_children():
            return []
        if self.first_child().type == ":":
            return Decl(self.state.but_with_first_child()).get_names()
        return [Decl(self.state.but_with(asl=child)).get_names()[0] for child in self.first_child()]

    def convert_let_args_to_var(self, type: Type):
        """For function arguments, if the declared type is unspecified, we should
        convert this to let types for structs"""
        if self.get_node_type() == "args":
            if type.is_tuple():
                for component in type.components:
                    if component.is_struct():
                        component.restriction = VarRestriction()
            elif type.is_struct():
                type.restriction = VarRestriction()
