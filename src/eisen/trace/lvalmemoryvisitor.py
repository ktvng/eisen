from __future__ import annotations

from alpaca.utils import Visitor

import eisen.adapters as adapters
from eisen.trace.entity import Trait
from eisen.trace.lval import Lval
from eisen.trace.attributevisitor import AttributeVisitor

from eisen.state.memoryvisitorstate import MemoryVisitorState

State = MemoryVisitorState
class LValMemoryVisitor(Visitor):
    def __init__(self, debug: bool = False):
        super().__init__(debug)

    def apply(self, state: State) -> list[Lval]:
        return self._route(state.get_ast(), state)

    @Visitor.for_ast_types("ref")
    def _ref(fn, state: State):
        return [Lval(name=adapters.Ref(state).get_name(),
                     memory=state.get_memory(adapters.Ref(state).get_name()),
                     trait=Trait())]

    @Visitor.for_ast_types(*adapters.BindingAST.ast_types)
    def _binding(fn, state: State):
        return fn.apply(state.but_with_first_child())

    @Visitor.for_ast_types("lvals", "bindings")
    def _lvals(fn, state: State):
        lvals = []
        for child in state.get_all_children():
            lvals += fn.apply(state.but_with(ast=child))
        return lvals

    @Visitor.for_tokens
    def _tokens(fn, state: State):
        name = state.get_ast().value
        return [Lval(name=name,
                     memory=state.get_memory(name),
                     trait=Trait())]

    @Visitor.for_ast_types(".")
    def _dot(fn, state: State):
        # if the attribute is a.b.c, the trait will be b.c
        return AttributeVisitor().get_lvals(state)
