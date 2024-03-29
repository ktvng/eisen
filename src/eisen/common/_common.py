from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from eisen.state.basestate import BaseState
    from eisen.common.eiseninstance import Instance

from alpaca.concepts import Type, Module

no_assign_binary_ops = ["+", "-", "/", "*", "and", "or"]
logic_ops = ["and", "or"]
math_ops = ["+", "-", "/", "*", "+=", "-=", "*=", "/="]
binary_ops = math_ops + logic_ops
equality_ops = ["==", "!="]
compare_ops = ["<", ">", "<=", ">="]
boolean_return_ops = compare_ops + equality_ops
implemented_primitive_types = ["str", "int", "bool", "flt"]

def asts_of_type(type: str, *args):
    def predicate(params: BaseState):
        return params.ast.type in list(args) + [type]
    return predicate

class Utils:
    global_prefix = ""

    # this should only be used when defining a struct. For all other uses, prefer
    # get_name_of_type
    @classmethod
    def get_full_name_of_struct(cls, name: str, mod: Module):
        return mod.get_full_name() + "_" + name

    @classmethod
    def get_full_name_of_function(cls, instance: Instance) -> str:
        prefix = ""
        current_context = instance.context
        while current_context:
            prefix = f"{current_context.name}_" + prefix
            current_context = current_context.parent

        return f"{Utils.global_prefix}{prefix}{instance.name}"

    @classmethod
    def get_name_of_type(cls, type: Type, mod: Module = None) -> str:
        if type.is_novel():
            return type.name
        elif type.is_struct():
            if mod is None:
                raise Exception("Module is required for name of struct type")
            return Utils.get_full_name_of_struct(type.name, mod)
        else:
            raise Exception(f"Unimplemented {type}")
