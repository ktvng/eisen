from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from eisen.common.state import State
from alpaca.concepts import TypeClass, Instance, Context, Module
from alpaca.clr import CLRList

binary_ops = ["+", "-", "/", "*", "and", "or", "+=", "-=", "*=", "/="] 
boolean_return_ops = ["<", ">", "<=", ">=", "==", "!=",]

def asls_of_type(type: str, *args):
    def predicate(params: State):
        return params.asl.type in list(args) + [type]
    return predicate
    
class EisenInstance(Instance):
    def __init__(self, name: str, type: TypeClass, context: Context, asl: CLRList, is_ptr=False, is_constructor=False):
        super().__init__(name, type, context, asl)
        self.is_ptr = is_ptr
        self.is_constructor = is_constructor
        self.is_var = False
        self.type: TypeClass = type

class Utils:
    global_prefix = ""

    # this should only be used when defining a struct. For all other uses, prefer
    # get_name_of_type
    @classmethod
    def get_full_name_of_struct(cls, name: str, mod: Module):
        prefix = ""
        current_mod = mod
        while current_mod:
            prefix = f"{current_mod.name}_" + prefix
            current_mod = current_mod.parent

        return f"{Utils.global_prefix}{prefix}{name}"     

    @classmethod
    def get_full_name_of_function(cls, instance: Instance) -> str:
        prefix = ""
        current_context = instance.context
        while current_context:
            prefix = f"{current_context.name}_" + prefix
            current_context = current_context.parent

        return f"{Utils.global_prefix}{prefix}{instance.name}"        

    @classmethod
    def get_name_of_type(cls, type: TypeClass, mod: Module = None) -> str:
        if type.is_novel():
            return type.name
        elif type.is_struct():
            if mod is None:
                raise Exception("Module is required for name of struct type")
            return Utils.get_full_name_of_struct(type.name, mod)
        else:
            raise Exception(f"Unimplemented {type}")