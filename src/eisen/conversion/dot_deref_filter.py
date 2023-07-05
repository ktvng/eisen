from __future__ import annotations

from alpaca.clr import ASTToken, AST
from alpaca.utils import Visitor

class DotDerefFilter(Visitor):
    def apply(self, ast: AST) -> AST:
        return self._route(ast, ast)

    @classmethod
    def is_dot_deref(cls, ast: AST):
        return (isinstance(ast, AST)
            and ast.type == "."
            and isinstance(ast.first(), AST)
            and ast.first().type == "deref")

    @Visitor.for_default
    def default_(fn, ast: AST):
        children = [fn.apply(child) for child in ast]
        ast._list = children
        return ast

    @Visitor.for_tokens
    def token_(fn, ast: AST) -> ASTToken:
        return ast

    @Visitor.for_ast_types(".")
    def dot_deref_(fn, ast: AST) -> AST:
        if DotDerefFilter.is_dot_deref(ast):
            ref_child = fn.apply(ast.first().first())
            tag_child = ast.second()
            return AST(
                type="->",
                lst=[ref_child, tag_child],
                line_number=ast.line_number,
                guid=ast.guid)
        return ast
