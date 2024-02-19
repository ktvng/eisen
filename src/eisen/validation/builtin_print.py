from __future__ import annotations

from alpaca.concepts import Type
from eisen.state.basestate import BaseState

class Builtins():
    @staticmethod
    def get_type_of_print(state: BaseState) -> Type:
        return state.get_type_factory().produce_function_type(
            args=state.get_void_type(),
            rets=state.get_void_type())
