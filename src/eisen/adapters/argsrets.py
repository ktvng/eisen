from __future__ import annotations

from alpaca.concepts import Type
from eisen.adapters.nodeinterface import AbstractNodeInterface

from eisen.adapters._decls import Typing

class ArgsRets(AbstractNodeInterface):
    ast_types = ["rets", "args"]
    examples = """
    (rets (: ...))
    (rets (prod_type ...))
    """

    def get_names(self) -> list[str]:
        if self.state.get_ast().has_no_children():
            return []
        if self.first_child().type == "prod_type":
            return [Typing(self.state.but_with(ast=child)).get_names()[0] for child in self.first_child()]
        return Typing(self.state.but_with_first_child()).get_names()
