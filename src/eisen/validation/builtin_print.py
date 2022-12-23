from __future__ import annotations

from alpaca.concepts import TypeClassFactory
from eisen.common.params import State

class BuiltinPrint():
    @classmethod
    def get_typeclass_of_function(cls, state: State):
        return TypeClassFactory.produce_function_type(
            arg=state.get_void_type(),
            ret=state.get_void_type(),
            mod=None)