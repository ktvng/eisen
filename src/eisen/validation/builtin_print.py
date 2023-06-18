from __future__ import annotations

from alpaca.concepts import TypeFactory, Type
from eisen.state.basestate import BaseState

class Builtins():
    @staticmethod
    def get_type_of_print(state: BaseState) -> Type:
        return TypeFactory.produce_function_type(
            arg=state.get_void_type(),
            ret=state.get_void_type(),
            mod=None)
