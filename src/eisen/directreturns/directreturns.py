from __future__ import annotations

from eisen.common.exceptions import Exceptions
from eisen.state.basestate import BaseState
from eisen.directreturns.directreturnsstate import DirectReturnsState as State
from alpaca.clr import AST, ASTToken
from alpaca.utils import Visitor

# Converts a direct return like this:
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

class DirectReturns(Visitor):
    def run(self, state: BaseState):
        self.apply(State.create_from_basestate(state))
        return state

    def apply(self, state: State):
        return self._route(state.get_ast(), state)

    @Visitor.for_default
    def default_(fn, state: State):
        for child in state.get_all_children():
            fn.apply(state.but_with(ast=child))

        return state.get_ast()

    @Visitor.for_tokens
    def tokens_(fn, state: State):
        pass

    @Visitor.for_ast_types("def")
    def def_(fn, state: State):
        # Get function's return tokens, if any
        rets = state.get_ast().third()
        if not len(rets):
            rets = []
        elif rets.first().type == "prod_type":
            rets = rets.first().get_all_children()
        else:
            rets = rets.get_all_children()
        rets = [ret.first().first() for ret in rets]

        for child in state.get_all_children():
            fn.apply(state.but_with(ast=child, rets=rets))

    @Visitor.for_ast_types("seq")
    def seq_(fn, state: State):
        new_children = []
        children = state.get_all_children()

        for child in children:
            new_child = fn.apply(state.but_with(ast=child))

            # Allow the return visitor to convert one child into multiple children in the sequence
            if isinstance(new_child, list):
                new_children += new_child
            else:
                new_children.append(new_child)

        children.clear()
        children += new_children

    @Visitor.for_ast_types("return")
    def return_(fn, state: State):
        rets = state.get_rets()
        ret_values = state.get_ast().items()

        if not ret_values:
            return state.get_ast()

        if ret_values[0].type == 'tuple':
            ret_values = ret_values[0].items()

        if len(rets) != len(ret_values):
            state.report_exception(Exceptions.ReturnValueCountMismatch(
                msg=f"got {len(ret_values)} return value(s), expected {len(rets)}",
                line_number=state.get_line_number()
            ))

        return [AST(type="=", lst=[AST(type="ref", lst=[ret]), val])
            for ret, val in zip(rets, ret_values)]
