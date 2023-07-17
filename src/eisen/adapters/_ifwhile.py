
from __future__ import annotations

from eisen.adapters.nodeinterface import AbstractNodeInterface

class If(AbstractNodeInterface):
    ast_type = "if"
    examples = """
    (if (cond ...) (cond ...))
    (if (cond ...) (seq ... ))
    """

    def enter_context_and_apply(self, fn):
        for child in self.state.get_child_asts():
            fn.apply(self.state.but_with(
                ast=child,
                context=self.state.create_block_context()))


class While(AbstractNodeInterface):
    ast_type = "while"
    examples = """
    (while (cond ...))
    """

    def enter_context_and_apply(self, fn):
        fn.apply(self.state.but_with(
            ast=self.state.first_child(),
            context=self.state.create_block_context()))

class Cond(AbstractNodeInterface):
    ast_type = "cond"
    examples = """
    (cond (...expression...) (seq ...))
    """

    def has_return_statement(self) -> bool:
        return Seq(self.state.but_with_second_child()).has_return_statement()

class Seq(AbstractNodeInterface):
    ast_type = "seq"
    examples = """
    (seq ...)
    """

    def has_return_statement(self) -> bool:
        for child in self.state.get_all_children():
            if child.type == "return":
                return True
        return False
