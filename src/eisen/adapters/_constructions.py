from __future__ import annotations

from alpaca.concepts import Type, Corpus
from alpaca.utils import Visitor
from alpaca.clr import AST
from eisen.adapters.nodeinterface import AbstractNodeInterface
from eisen.adapters._decls import Colon

class _SharedMixins:
    _get_name = AbstractNodeInterface.get_name_from_first_child
    get_name = AbstractNodeInterface.get_name_from_first_child

    def get_this_type(self) -> Type:
        corpus: Corpus = self.state.get_corpus()
        return corpus.get_type(name=self.get_name(),
                               environmental_namespace=None,
                               specified_namespace=self.state.get_enclosing_module().get_namespace_str())

    def get_child_attribute_asts(self) -> list[AST]:
        return [child for child in self.state.get_ast()
                if child.type == ":" or child.type == ":="]

    def get_child_attribute_names(self) -> list[str]:
        child_asts = self.get_child_attribute_asts()
        return [Colon(self.state.but_with(ast=ast)).get_name() for ast in child_asts]

    def get_child_attribute_bindings(self) -> list[str]:
        child_asts = self.get_child_attribute_asts()
        return [Colon(self.state.but_with(ast=child)).get_binding() for child in child_asts]


class Struct(AbstractNodeInterface, _SharedMixins):
    ast_type = "struct"
    examples = """
    (struct name
        (impls ...)
        (: ...)
        (: ...)
        (create ...))
    """
    def implements_interfaces(self) -> bool:
        return (len(self.state.get_ast()) >= 2
            and isinstance(self.second_child(), AST)
            and self.second_child().type == "impls")

    def get_impls_ast(self) -> AST:
        return self.second_child()

    def _get_embed_asts(self) -> list[AST]:
        return [child for child in self.state.get_ast() if child.type == "embed"]

    def has_create_ast(self) -> bool:
        create_asts = [child for child in self.state.get_ast() if child.type == "create"]
        return len(create_asts) == 1

    def get_create_ast(self) -> AST:
        create_asts = [child for child in self.state.get_ast() if child.type == "create"]
        return create_asts[0]

    def apply_fn_to_create_ast(self, fn: Visitor) -> None:
        if self.has_create_ast():
            fn.apply(self.state.but_with(ast=self.get_create_ast()))

class Trait(AbstractNodeInterface, _SharedMixins):
    ast_type = "trait"
    examples = """
    (trait name
        (: ...)
        (: ...))
    """

class TraitDef(AbstractNodeInterface):
    ast_type = "trait_def"
    examples = """
    (trait_def name for obj_name
        (def ...)
        (def ...))
    """

    def get_trait_name(self) -> str:
        return self.first_child().value

    def get_struct_name(self) -> str:
        return self.second_child().value

    def get_asts_of_implemented_functions(self) -> list[AST]:
        return self.state.get_child_asts()

    def apply_fn_to_all_defined_functions(self, fn: Visitor):
        for child in self.get_asts_of_implemented_functions():
            fn.apply(self.state.but_with(ast=child))
