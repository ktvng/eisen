
from __future__ import annotations

from eisen.nodes.nodeinterface import AbstractNodeInterface

class If(AbstractNodeInterface):
    asl_type = "if"
    examples = """
    (if (cond ...) (cond ...))
    (if (cond ...) (seq ... ))
    """

    def enter_context_and_apply(self, fn):
        for child in self.state.get_child_asls():
            fn.apply(self.state.but_with(
                asl=child,
                context=self.state.create_block_context()))


class While(AbstractNodeInterface):
    asl_type = "while"
    examples = """
    (while (cond ...))
    """

    def enter_context_and_apply(self, fn):
        fn.apply(self.state.but_with(
            asl=self.state.first_child(),
            context=self.state.create_block_context()))
