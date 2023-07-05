from __future__ import annotations

from alpaca.concepts import Type
from alpaca.clr import AST, ASTToken
from eisen.adapters.nodeinterface import AbstractNodeInterface

class Struct(AbstractNodeInterface):
    ast_type = "struct"
    examples = """
    (struct name
        (impls ...)
        (: ...)
        (: ...)
        (create ...))
    """
    _get_name = AbstractNodeInterface.get_name_from_first_child
    get_struct_name = AbstractNodeInterface.get_name_from_first_child
    get_this_type = AbstractNodeInterface.get_type_for_node_that_defines_a_type

    def implements_interfaces(self) -> bool:
        return (len(self.state.get_ast()) >= 2
            and isinstance(self.second_child(), AST)
            and self.second_child().type == "impls")

    def get_impls_ast(self) -> AST:
        return self.second_child()

    def get_implemented_interfaces(self) -> list[Type]:
        interfaces = []
        if self.implements_interfaces():
            for child in self.get_impls_ast():
                interfaces.append(self.state.get_defined_type(child.value))
                # TODO: currently we only allow the interface to be looked up in the same
                # module as the struct. In general, we need to allow interfaces from arbitrary
                # modules.
        return interfaces

    def _get_embed_asts(self) -> list[AST]:
        return [child for child in self.state.get_ast() if child.type == "embed"]

    def _parse_embed_ast_for_types(self, embed_ast: AST) -> list[Type]:
        # TODO: currently we only allow the interface to be looked up in the same
        # module as the struct. In general, we need to allow interfaces from arbitrary
        # modules.
        if isinstance(embed_ast.first(), AST):
            return [self.state.get_defined_type(child.value) for child in embed_ast.first()]
        return [self.state.get_defined_type(embed_ast.first().value)]

    def get_embedded_structs(self) -> list[Type]:
        embedded_structs: list[Type] = []
        embed_asts = self._get_embed_asts()
        for ast in embed_asts:
            embedded_structs.extend(self._parse_embed_ast_for_types(ast))

        return embedded_structs

    def get_child_attribute_asts(self) -> list[AST]:
        return [child for child in self.state.get_ast()
                if child.type == ":" or child.type == ":=" or child.type == "mut" or child.type == "let" or child.type == "val"]

    def get_child_attribute_names(self) -> list[str]:
        child_asts = self.get_child_attribute_asts()
        return [ast.first().value for ast in child_asts]

    def has_create_ast(self) -> bool:
        create_asts = [child for child in self.state.get_ast() if child.type == "create"]
        return len(create_asts) == 1

    def get_create_ast(self) -> AST:
        create_asts = [child for child in self.state.get_ast() if child.type == "create"]
        return create_asts[0]


class Variant(AbstractNodeInterface):
    ast_type = "variant"
    examples = """
    (variant name
        (is ...)
        (@allow ...)
        (@deny ...))
    """
    _get_name = AbstractNodeInterface.get_name_from_first_child
    get_variant_name = AbstractNodeInterface.get_name_from_first_child
    get_this_type = AbstractNodeInterface.get_type_for_node_that_defines_a_type

    def get_token_defining_parent(self) -> ASTToken:
        return self.state.second_child()

    def get_parent_type(self) -> Type:
        parent_type_name = self.get_token_defining_parent().value
        return self.state.get_defined_type(parent_type_name)

    def get_is_ast(self) -> AST:
        for child in self.state.get_child_asts():
            if child.type == "is_fn":
                return child
        raise Exception(f"expected an 'is_fn' ast for variant: {self.get_variant_name()}")


class Interface(AbstractNodeInterface):
    ast_type = "interface"
    examples = """
    (interface name
        (impls ...)
        (: ...)
        (: ...)
    """
    _get_name = AbstractNodeInterface.get_name_from_first_child
    get_interface_name = AbstractNodeInterface.get_name_from_first_child
    get_this_type = AbstractNodeInterface.get_type_for_node_that_defines_a_type

    def get_child_attribute_asts(self) -> list[AST]:
        return [child for child in self.state.get_ast() if child.type == ":"]

    def get_child_attribute_names(self) -> list[str]:
        child_asts = self.get_child_attribute_asts()
        return [ast.first().value for ast in child_asts]
