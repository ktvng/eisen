from __future__ import annotations

from alpaca.concepts import TypeFactory
from eisen.common.state import State

class BuiltinPrint():
    @classmethod
    def get_type_of_function(cls, state: State):
        return TypeFactory.produce_function_type(
            arg=state.get_void_type(),
            ret=state.get_void_type(),
            mod=None)