from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from seer.common.params import Params
from alpaca.concepts import TypeClass, Instance, Context
from alpaca.clr import CLRList

Module = Context

binary_ops = ["+", "-", "/", "*", "and", "or", "+=", "-=", "*=", "/="] 
boolean_return_ops = ["<", ">", "<=", ">=", "==", "!=",]

class ContextTypes:
    mod = "module"
    fn = "fn"
    block = "block"

def asls_of_type(type: str, *args):
    def predicate(params: Params):
        return params.asl.type in list(args) + [type]
    return predicate
    
class SeerInstance(Instance):
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
    def get_full_name_of_struct(cls, name: str, context: Context):
        prefix = ""
        current_context = context
        while current_context:
            prefix = f"{current_context.name}_" + prefix
            current_context = current_context.parent

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
    def get_name_of_type(cls, type: TypeClass, mod: Context = None) -> str:
        if type.is_novel():
            return type.name
        elif type.is_struct():
            if mod is None:
                raise Exception("context is required for name of struct type")
            return Utils.get_full_name_of_struct(type.name, mod)
        else:
            raise Exception(f"Unimplemented {type}")