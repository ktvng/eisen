from __future__ import annotations

from alpaca.concepts._type import Type
from alpaca.concepts._module import Module

class TypeFactory():
    @classmethod
    def produce_novel_type(cls, name: str) -> Type:
        return Type(
            classification=Type.classifications.novel,
            name=name,
            mod=None,
            components=[],
            component_names=[],
            inherits=[],
            embeds=[],
            parametrics=[],
            restriction=None,
            parent_type=None)

    @classmethod
    def produce_tuple_type(cls, components: list[Type]) -> Type:
        return Type(
            classification=Type.classifications.tuple,
            name="",
            mod=None,
            components=components,
            component_names=[],
            inherits=[],
            embeds=[],
            parametrics=[],
            restriction=None,
            parent_type=None)

    @classmethod
    def produce_parametric_type(cls, name: str, parametrics: list[Type]) -> Type:
        return Type(
            classification=Type.classifications.parametric,
            name=name,
            mod=None,
            components=[],
            component_names=[],
            inherits=[],
            embeds=[],
            parametrics=parametrics,
            restriction=None,
            parent_type=None)


    # TODO: function types should not need modules, unless they are named
    @classmethod
    def produce_function_type(cls, arg: Type, ret: Type, mod: Module, name: str = "") -> Type:
        return Type(
            classification=Type.classifications.function,
            name=name,
            mod=mod,
            components=[arg, ret],
            component_names=["arg", "ret"],
            inherits=[],
            embeds=[],
            parametrics=[],
            restriction=None,
            parent_type=None)

    @classmethod
    def produce_proto_struct_type(cls, name: str, mod: Module) -> Type:
        return Type(
            classification=Type.classifications.proto_struct,
            name=name,
            mod=mod,
            components=[],
            component_names=[],
            inherits=[],
            embeds=[],
            parametrics=[],
            restriction=None,
            parent_type=None)

    @classmethod
    def produce_proto_interface_type(cls, name: str, mod: Module) -> Type:
        return Type(
            classification=Type.classifications.proto_interface,
            name=name,
            mod=mod,
            components=[],
            component_names=[],
            inherits=[],
            embeds=[],
            parametrics=[],
            restriction=None,
            parent_type=None)

    @classmethod
    def produce_proto_variant_type(cls, name: str, mod: Module) -> Type:
        return Type(
            classification=Type.classifications.proto_variant,
            name=name,
            mod=mod,
            components=[],
            component_names=[],
            inherits=[],
            embeds=[],
            parametrics=[],
            restriction=None,
            parent_type=None)

    @classmethod
    def produce_nil_type(cls) -> Type:
        return Type(
            classification=Type.classifications.nil,
            name="nil",
            mod=None,
            components=[],
            component_names=[],
            inherits=[],
            embeds=[],
            parametrics=[],
            restriction=None,
            parent_type=None)
