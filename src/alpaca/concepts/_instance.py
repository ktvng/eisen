from __future__ import annotations

from alpaca.concepts._type import Type
from alpaca.concepts._context import Context

class Instance():
    def __init__(self, name: str, type: Type, context: Context):
        self.name = name
        self.type = type
        self.context = context

    def __str__(self) -> str:
        return f"{self.name}{self.type}"
        