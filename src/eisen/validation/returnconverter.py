from __future__ import annotations

from eisen.common.nodedata import NodeData
from eisen.common.exceptions import Exceptions
from eisen.state.basestate import BaseState as State
from alpaca.clr import AST, ASTToken
from alpaca.utils import Visitor

class ReturnConverter(Visitor):
    def run(self, state: State):
        self.apply(state)
        return state

    def apply(self, state: State):
        return self._route(state.get_ast(), state)

    @Visitor.for_default
    def default_(fn, state: State):
        for child in state.get_all_children():
            fn.apply(state.but_with(ast=child))

    @Visitor.for_tokens
    def tokens_(fn, state: State):
        pass

    @Visitor.for_ast_types("def")
    def def_(fn, state: State):
        # Get function's return tokens, if any
        #
        # TODO: validate return types?
        # Q: do we need to handle `fn TAG ARGS SEQ` (no `RETS`) from the grammar?
        rets = state.get_ast().third()
        if not len(rets):
            rets = []
        elif rets.first().type == "prod_type":
            rets = rets.first().get_all_children()
        else:
            rets = rets.get_all_children()
        rets = [ret.first().first() for ret in rets]

        context = state.create_isolated_context()
        context.add_entity("rets", rets)

        for child in state.get_all_children():
            fn.apply(state.but_with(ast=child, context=context))

    @Visitor.for_ast_types("seq")
    def seq_(fn, state: State):
        # Convert a direct return like this:
        #
        #   def foo() -> a: int, b: int {
        #     return 1, 2
        #   }
        #
        # into this:
        #
        #   def foo() -> a: int, b: int {
        #     a = 1
        #     b = 2
        #     return
        #   }
        #
        # so that the interpreter can run it without needing to know about direct returns.
        context = state.get_context()
        rets = context.get_entity("rets") if context else []
        children = state.get_all_children()
        i = 0
        while i < len(children):
            child = children[i]
            if child.type == "return" and (ret_values := child.items()):
                if ret_values[0].type == 'tuple':
                    ret_values = ret_values[0].items()

                if len(rets) == len(ret_values):
                    for j, val in enumerate(ret_values):
                        children.insert(i, AST(type="=", lst=[AST(type="ref", lst=[rets[j]]), val]))
                        i += 1
                else:
                    state.report_exception(Exceptions.ReturnValueCountMismatch(
                        msg=f"got {len(ret_values)} return value(s), expected {len(rets)}",
                        line_number=child.line_number
                    ))
            i += 1

        for child in children:
           fn.apply(state.but_with(ast=child))
