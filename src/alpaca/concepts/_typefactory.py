from __future__ import annotations

from alpaca.concepts._type import (Type, FunctionType, TupleType, StructType, InterfaceType,
                                   NovelType, VariantType, NilType, ParametricType)
from alpaca.concepts._module import Module

class TypeFactory():
    @staticmethod
    def produce_novel_type(name: str) -> Type:
        return NovelType(name)

    @staticmethod
    def produce_tuple_type(components: list[Type]) -> Type:
        return TupleType(components)

    @staticmethod
    def produce_parametric_type(name: str, parametrics: list[Type]) -> Type:
        return ParametricType(name, parametrics)

    # TODO: function types should not need modules, unless they are named
    @staticmethod
    def produce_function_type(arg: Type, ret: Type, mod: Module, name: str = "") -> Type:
        return FunctionType(name, mod, arg, ret)

    @staticmethod
    def produce_proto_struct_type(name: str, mod: Module) -> Type:
        return StructType(name, mod)

    @staticmethod
    def produce_proto_interface_type(name: str, mod: Module) -> Type:
        return InterfaceType(name, mod)

    @staticmethod
    def produce_proto_variant_type(name: str, mod: Module) -> Type:
        return VariantType(name, mod)

    @staticmethod
    def produce_nil_type() -> Type:
        return NilType()
