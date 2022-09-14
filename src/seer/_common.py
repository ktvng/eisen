from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from seer._params import Params
from alpaca.concepts import Type, Instance, Context
from alpaca.clr import CLRList

class ContextTypes:
    mod = "module"
    fn = "fn"
    block = "block"

def asls_of_type(type: str, *args):
    def predicate(params: Params):
        return params.asl.type in list(args) + [type]
    return predicate
    
class SeerInstance(Instance):
    def __init__(self, name: str, type: Type, context: Context, asl: CLRList, is_ptr=False):
        super().__init__(name, type, context, asl)
        self.is_ptr = is_ptr
