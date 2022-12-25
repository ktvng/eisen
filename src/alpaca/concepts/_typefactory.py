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
            restriction=None)

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
            restriction=None)

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
            restriction=None)

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
            restriction=None)

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
            restriction=None)
