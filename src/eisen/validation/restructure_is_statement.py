from __future__ import annotations

from alpaca.clr import AST, ASTToken

from eisen.common.nodedata import NodeData
from eisen.state.basestate import BaseState
import eisen.adapters as adapters

class RestructureIsStatement():
    @classmethod
    def run(cls, state: BaseState):
        node = adapters.Is(state)
        is_ast = state.get_ast()
        new_token = ASTToken(type_chain=["TAG"], value="is_" + node.get_type_name())
        new_ref = AST(type="fn", lst=[new_token], line_number=is_ast.line_number, data=NodeData())
        new_params = AST(type="params", lst=[is_ast.first()], line_number=is_ast.line_number, data=NodeData())
        is_ast.update(type="is_call", lst=[new_ref, new_params])
