from __future__ import annotations

from alpaca.concepts import TypeFactory as BaseTypeFactory, Type, Module
from eisen.common.binding import Binding
class TypeFactory:
    @staticmethod
    def produce_novel_type(name: str) -> Type:
        if name == "void": return BaseTypeFactory.produce_novel_type("void")
        return BaseTypeFactory.produce_novel_type(name).with_modifier(Binding.data)

    @staticmethod
    def produce_tuple_type(components: list[Type]) -> Type:
        return BaseTypeFactory.produce_tuple_type(components)

    @staticmethod
    def produce_parametric_type(name: str, parametrics: list[Type]) -> Type:
        return BaseTypeFactory.produce_parametric_type(name, parametrics)

    # TODO: function types should not need modules, unless they are named
    @staticmethod
    def produce_function_type(arg: Type,
                              ret: Type,
                              mod: Module,
                              name: str = "") -> Type:
        return BaseTypeFactory.produce_function_type(arg, ret, mod, name).with_modifier(Binding.void)

    @staticmethod
    def produce_proto_struct_type(name: str, mod: Module) -> Type:
        return BaseTypeFactory.produce_proto_struct_type(name, mod)

    @staticmethod
    def produce_proto_interface_type(name: str, mod: Module) -> Type:
        return BaseTypeFactory.produce_proto_interface_type(name, mod)

    @staticmethod
    def produce_nil_type() -> Type:
        return BaseTypeFactory.produce_nil_type()

    @staticmethod
    def produce_void_type() -> Type:
        return TypeFactory.produce_novel_type("void")

    @staticmethod
    def produce_curried_function_type(fn_type: Type, curried_args_type: Type) -> Type:
        """
        Assumes all validations are complete. Obtain the new function type after
        currying the [curried_args_type]
        """
        n_curried_args = len(curried_args_type.unpack_into_parts())
        remaining_args = fn_type.get_argument_type().unpack_into_parts()[n_curried_args: ]

        match len(remaining_args):
            case 0:
                new_argument_type = TypeFactory.produce_void_type()
            case 1:
                new_argument_type = remaining_args[0]
            case _:
                new_argument_type = TypeFactory.produce_tuple_type(components=remaining_args)

        return TypeFactory.produce_function_type(
            arg=new_argument_type,
            ret=fn_type.get_return_type(),
            mod=fn_type.mod).with_modifier(Binding.new)
