from __future__ import annotations

from alpaca.concepts import TypeFactory as BaseTypeFactory, Type, Module
from eisen.state.typecheckerstate import TypeCheckerState
from eisen.common.restriction import ImmutableRestriction, Restrictions, GeneralRestriction

State = TypeCheckerState
class TypeFactory:
    @staticmethod
    def produce_novel_type(name: str) -> Type:
        return BaseTypeFactory.produce_novel_type(name)\
            .with_restriction(Restrictions.Data())

    @staticmethod
    def produce_tuple_type(components: list[Type]) -> Type:
        return BaseTypeFactory.produce_tuple_type(components)\
            .with_restriction(Restrictions.Void())

    @staticmethod
    def produce_parametric_type(name: str, parametrics: list[Type]) -> Type:
        return BaseTypeFactory.produce_parametric_type(name, parametrics)\
            .with_restriction(Restrictions.Void())

    # TODO: function types should not need modules, unless they are named
    @staticmethod
    def produce_function_type(arg: Type,
                              ret: Type,
                              mod: Module,
                              name: str = "",
                              restriction: GeneralRestriction = None) -> Type:
        return BaseTypeFactory.produce_function_type(arg, ret, mod, name)\
            .with_restriction(restriction if restriction is not None else Restrictions.Void())

    @staticmethod
    def produce_proto_struct_type(name: str, mod: Module) -> Type:
        return BaseTypeFactory.produce_proto_struct_type(name, mod)\
            .with_restriction(Restrictions.Void())

    @staticmethod
    def produce_proto_interface_type(name: str, mod: Module) -> Type:
        return BaseTypeFactory.produce_proto_interface_type(name, mod)\
            .with_restriction(Restrictions.Void())

    @staticmethod
    def produce_proto_variant_type(name: str, mod: Module) -> Type:
        return BaseTypeFactory.produce_proto_variant_type(name, mod)\
            .with_restriction(Restrictions.Void())

    @staticmethod
    def produce_nil_type() -> Type:
        return BaseTypeFactory.produce_nil_type()\
            .with_restriction(Restrictions.Void())

    @staticmethod
    def produce_curried_function_type(fn_type: Type, curried_args_type: Type) -> Type:
        """
        Assumes all validations are complete. Obtain the new function type after
        currying the [curried_args_type]
        """
        n_curried_args = len(curried_args_type.unpack_into_parts())
        remaining_args = fn_type.get_argument_type().unpack_into_parts()[n_curried_args: ]

        new_argument_type = remaining_args[0] if len(remaining_args) == 1 else (
            TypeFactory.produce_tuple_type(components=remaining_args))

        return TypeFactory.produce_function_type(
            arg=new_argument_type,
            ret=fn_type.get_return_type(),
            mod=fn_type.mod,
            restriction=Restrictions.New())
