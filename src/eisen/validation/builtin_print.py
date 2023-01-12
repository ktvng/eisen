from __future__ import annotations

from alpaca.concepts import TypeFactory, Type
from eisen.common.state import State

class BuiltinPrint():
    @classmethod
    def get_type_of_function(cls, state: State) -> Type:
        return TypeFactory.produce_function_type(
            arg=state.get_void_type(),
            ret=state.get_void_type(),
            mod=None)
