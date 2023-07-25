from __future__ import annotations

from alpaca.clr import AST, ASTToken, ASTElement
from alpaca.concepts import Type
from eisen.adapters.nodeinterface import AbstractNodeInterface

class Annotation(AbstractNodeInterface):
    ast_type = "annotation"
    examples = """
    (annotation annotation_name any number of tokens)
    """

    def get_string_value(self, ast: ASTElement) -> str:
        match ast:
            case AST(type="ref"): return ast.first().value
            case ASTToken(): return ast.value
            case _: raise Exception("not implemented")

    def get_annotation_type(self) -> str:
        return self.get_string_value(self.first_child())

    def get_annotation_arguments(self) -> list[str]:
        return [self.get_string_value(ast) for ast in self.state.get_all_children()][1: ]

class CompilerAssertAnnotation(Annotation):
    ast_type = "annotation"
    examples = """
    (annotation compiler_assert function_name args0 args1 ...)
    """

    def get_functionality(self) -> str:
        return self.get_string_value(self.second_child())

    def get_annotation_arguments(self) -> list[str]:
        return [self.get_string_value(ast) for ast in self.state.get_all_children()][2: ]
