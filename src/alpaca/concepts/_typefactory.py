from __future__ import annotations

from alpaca.concepts._type import (Type, FunctionType, TupleType, StructType, InterfaceType,
                                   NovelType, VariantType, NilType, ParametricType)
from alpaca.concepts._module import Module

class TypeFactory():
    @classmethod
    def produce_novel_type(cls, name: str) -> Type:
        return NovelType(name)

    @classmethod
    def produce_tuple_type(cls, components: list[Type]) -> Type:
        return TupleType(components)

    @classmethod
    def produce_parametric_type(cls, name: str, parametrics: list[Type]) -> Type:
        return ParametricType(name, parametrics)

    # TODO: function types should not need modules, unless they are named
    @classmethod
    def produce_function_type(cls, arg: Type, ret: Type, mod: Module, name: str = "") -> Type:
        return FunctionType(name, mod, arg, ret)

    @classmethod
    def produce_proto_struct_type(cls, name: str, mod: Module) -> Type:
        return StructType(name, mod)

    @classmethod
    def produce_proto_interface_type(cls, name: str, mod: Module) -> Type:
        return InterfaceType(name, mod)

    @classmethod
    def produce_proto_variant_type(cls, name: str, mod: Module) -> Type:
        return VariantType(name, mod)

    @classmethod
    def produce_nil_type(cls) -> Type:
        return NilType()
