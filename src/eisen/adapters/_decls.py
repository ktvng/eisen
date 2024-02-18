from __future__ import annotations

from alpaca.clr import AST
from eisen.adapters.nodeinterface import AbstractNodeInterface
from eisen.common.binding import Binding

class BindingAST(AbstractNodeInterface):
    ast_types = ["var", "new", "mut", "void", "mut_new", "mut_var", "move"]
    examples = """
    (var x)
    (new self)
    (mut y)
    """

    def get_name(self) -> str:
        return self.first_child().value

    def get_binding(self) -> Binding:
        match self.get_ast_type():
            case "ret_new": return Binding.ret_new
            case "new": return Binding.new
            case "mut_new": return Binding.mut_new

            case "fixed": return Binding.fixed
            case "mut": return Binding.mut

            case "var": return Binding.var
            case "mut_var": return Binding.mut_var

            case "mut_star": return Binding.mut_star

            case "move": return Binding.move
            case "void": return Binding.void
            case _: raise Exception(f"not implemented for {self.get_ast_type()}")

class _SharedMixins():
    def is_single_assignment(self) -> bool:
        return self.first_child().type != "bindings"

    def get_names(self) -> list[str]:
        match self.is_single_assignment():
            case True: return [BindingAST(self.state.but_with_first_child()).get_name()]
            case False: return [BindingAST(self.state.but_with(ast=child)).get_name() for child in self.first_child()]

    def get_bindings(self) -> list[Binding]:
        match self.is_single_assignment():
            case True: return [BindingAST(self.state.but_with_first_child()).get_binding()]
            case False: return [BindingAST(self.state.but_with(ast=child)).get_binding() for child in self.first_child()]

class TypeLike(AbstractNodeInterface):
    ast_types = ["type"]
    examples = """
    (type name)
    """
    get_name = AbstractNodeInterface.get_name_from_first_child

    def get_is_nilable(self) -> bool:
        return self.get_ast_type() == "nilable_type"

class InferenceAssign(AbstractNodeInterface, _SharedMixins):
    ast_types = ["ilet"]
    examples = """
    1. (ilet (var name) (call ...))
    2. (ilet (var name) 4)
    3. (ilet (mut name) (<expression>))
    4. (ilet (tags ...) (tuple ...))
    5. (ilet (tags ...) (call ...))
    """
    def get_is_nilable(self) -> bool:
        match self.get_ast_type():
            case "inil?": return True
            case _: return False

class Colon(AbstractNodeInterface):
    ast_types = [":"]
    examples = """
    (: (var x) (type type_name))
    """

    def get_name(self) -> str:
        return BindingAST(self.state.but_with_first_child()).get_name()

    def get_binding(self) -> Binding:
        return BindingAST(self.state.but_with_first_child()).get_binding()

    def get_type_ast(self) -> AST:
        return self.second_child()

class Decl(AbstractNodeInterface, _SharedMixins):
    ast_types = ["let"]
    examples = """
    1. multiple assignment
        (let (bindings ...) (type ...))
    2. single_assignment
        (let (binding name) (type ...))
    """
    def get_is_nilable(self) -> bool:
        return self.get_ast_type() == "nil?"

class Typing(AbstractNodeInterface, _SharedMixins):
    ast_types = ["let", ":"]
    examples = """
    See Colon and Decl classes. This class can be used in lieu of these two
    """
    def get_is_nilable(self) -> bool:
        match self.get_ast_type():
            case ":": return TypeLike(self.state.but_with_second_child()).get_is_nilable()
            case _: return Decl(self.state).get_is_nilable()

    def get_type_ast(self) -> AST:
        return self.second_child()
