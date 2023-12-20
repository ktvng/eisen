from __future__ import annotations
import uuid

from eisen.trace.shadow import Shadow
from eisen.trace.entity import Angel
from eisen.trace.memory import Memory

class FunctionDelta():
    def __init__(self,
                 function_name: str,
                 arg_shadows: list[Shadow],
                 ret_shadows: list[Shadow],
                 angels: list[Angel],
                 angel_shadows: dict[uuid.UUID, Shadow],
                 ret_memories: list[Memory]) -> None:

        self.function_name = function_name
        self.arg_shadows = arg_shadows
        self.ret_shadows = ret_shadows
        self.angels = angels
        self.angel_shadows = angel_shadows
        self.ret_memories = ret_memories

class FunctionDB():
    def __init__(self) -> None:
        self._function_deltas: dict[str, FunctionDelta] = {}

    def add_function_delta(self, name: str, fc: FunctionDelta):
        self._function_deltas[name] = fc

    def get_function_delta(self, name: str) -> FunctionDelta:
        return self._function_deltas.get(name, None)
