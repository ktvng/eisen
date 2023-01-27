from __future__ import annotations

from alpaca.concepts import Type
from alpaca.clr import CLRList, CLRToken
from eisen.nodes.nodeinterface import AbstractNodeInterface

class Struct(AbstractNodeInterface):
    asl_type = "struct"
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
        return (len(self.state.get_asl()) >= 2
            and isinstance(self.second_child(), CLRList)
            and self.second_child().type == "impls")

    def get_impls_asl(self) -> CLRList:
        return self.second_child()

    def get_implemented_interfaces(self) -> list[Type]:
        interfaces = []
        if self.implements_interfaces():
            for child in self.get_impls_asl():
                interfaces.append(self.state.get_defined_type(child.value))
                # TODO: currently we only allow the interface to be looked up in the same
                # module as the struct. In general, we need to allow interfaces from arbitrary
                # modules.
        return interfaces

    def _get_embed_asls(self) -> list[CLRList]:
        return [child for child in self.state.get_asl() if child.type == "embed"]

    def _parse_embed_asl_for_types(self, embed_asl: CLRList) -> list[Type]:
        # TODO: currently we only allow the interface to be looked up in the same
        # module as the struct. In general, we need to allow interfaces from arbitrary
        # modules.
        if isinstance(embed_asl.first(), CLRList):
            return [self.state.get_defined_type(child.value) for child in embed_asl.first()]
        return [self.state.get_defined_type(embed_asl.first().value)]

    def get_embedded_structs(self) -> list[Type]:
        embedded_structs: list[Type] = []
        embed_asls = self._get_embed_asls()
        for asl in embed_asls:
            embedded_structs.extend(self._parse_embed_asl_for_types(asl))

        return embedded_structs

    def get_child_attribute_asls(self) -> list[CLRList]:
        return [child for child in self.state.get_asl() if child.type == ":" or child.type == ":="]

    def get_child_attribute_names(self) -> list[str]:
        child_asls = self.get_child_attribute_asls()
        return [asl.first().value for asl in child_asls]

    def has_create_asl(self) -> bool:
        create_asls = [child for child in self.state.get_asl() if child.type == "create"]
        return len(create_asls) == 1

    def get_create_asl(self) -> CLRList:
        create_asls = [child for child in self.state.get_asl() if child.type == "create"]
        return create_asls[0]


class Variant(AbstractNodeInterface):
    asl_type = "variant"
    examples = """
    (variant name
        (is ...)
        (@allow ...)
        (@deny ...))
    """
    _get_name = AbstractNodeInterface.get_name_from_first_child
    get_variant_name = AbstractNodeInterface.get_name_from_first_child
    get_this_type = AbstractNodeInterface.get_type_for_node_that_defines_a_type

    def get_token_defining_parent(self) -> CLRToken:
        return self.state.second_child()

    def get_parent_type(self) -> Type:
        parent_type_name = self.get_token_defining_parent().value
        return self.state.get_defined_type(parent_type_name)

    def get_is_asl(self) -> CLRList:
        for child in self.state.get_child_asls():
            if child.type == "is_fn":
                return child
        raise Exception(f"expected an 'is_fn' asl for variant: {self.get_variant_name()}")


class Interface(AbstractNodeInterface):
    asl_type = "interface"
    examples = """
    (interface name
        (impls ...)
        (: ...)
        (: ...)
    """
    _get_name = AbstractNodeInterface.get_name_from_first_child
    get_interface_name = AbstractNodeInterface.get_name_from_first_child
    get_this_type = AbstractNodeInterface.get_type_for_node_that_defines_a_type

    def get_child_attribute_asls(self) -> list[CLRList]:
        return [child for child in self.state.get_asl() if child.type == ":"]

    def get_child_attribute_names(self) -> list[str]:
        child_asls = self.get_child_attribute_asls()
        return [asl.first().value for asl in child_asls]
