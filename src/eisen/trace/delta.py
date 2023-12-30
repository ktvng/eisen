from __future__ import annotations
import uuid
from dataclasses import dataclass

from eisen.trace.shadow import Shadow
from eisen.trace.entity import Angel
from eisen.trace.memory import Memory

@dataclass
class FunctionDelta():
    """
    A FunctionDelta represents how calling a function on a generic set of parameters
    may permute the dependencies of the parameters. Any changes that the function would make
    to the parameters, as well as any return value dependencies are recorded by the FunctionDelta
    and can be replayed wherever the function is called to impart these changes.
    """
    function_name: str
    arg_shadows: list[Shadow]
    ret_shadows: list[Shadow]
    angels: list[Angel]
    angel_shadows: dict[uuid.UUID, Shadow]
    ret_memories: list[Memory]

class FunctionDB():
    """
    A wrapper around a dictionary mapping the FQDN of a function (str) to its computed
    FunctionDelta.
    """

    def __init__(self) -> None:
        self._function_deltas: dict[str, FunctionDelta] = {}

    def add_function_delta(self, name: str, fc: FunctionDelta):
        self._function_deltas[name] = fc

    def get_function_delta(self, name: str) -> FunctionDelta:
        return self._function_deltas.get(name, None)
