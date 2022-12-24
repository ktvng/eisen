from __future__ import annotations

from alpaca.concepts._typeclass import TypeClass
from alpaca.concepts._module import Module

class TypeClassFactory():
    @classmethod
    def produce_novel_type(cls, name: str) -> TypeClass:
        return TypeClass(
            classification=TypeClass.classifications.novel, 
            name=name, 
            mod=None, 
            components=[], 
            component_names=[], 
            inherits=[],
            embeds=[],
            restriction=None)

    @classmethod
    def produce_tuple_type(cls, components: list[TypeClass]) -> TypeClass:
        return TypeClass(
            classification=TypeClass.classifications.tuple, 
            name="",
            mod=None, 
            components=components, 
            component_names=[], 
            inherits=[],
            embeds=[],
            restriction=None)

    @classmethod
    def produce_function_type(cls, arg: TypeClass, ret: TypeClass, mod: Module, name: str = "") -> TypeClass:
        return TypeClass(
            classification=TypeClass.classifications.function, 
            name=name, 
            mod=mod, 
            components=[arg, ret], 
            component_names=["arg", "ret"], 
            inherits=[],
            embeds=[],
            restriction=None)

    @classmethod
    def produce_proto_struct_type(cls, name: str, mod: Module) -> TypeClass:
        return TypeClass(
            classification=TypeClass.classifications.proto_struct,
            name=name, 
            mod=mod, 
            components=[], 
            component_names=[], 
            inherits=[],
            embeds=[],
            restriction=None)

    @classmethod
    def produce_proto_interface_type(cls, name: str, mod: Module) -> TypeClass:
        return TypeClass(
            classification=TypeClass.classifications.proto_interface, 
            name=name, 
            mod=mod, 
            components=[], 
            component_names=[], 
            inherits=[],
            embeds=[],
            restriction=None)
