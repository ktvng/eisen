from __future__ import annotations

from alpaca.concepts._type import Type
from alpaca.concepts._context import Context
from alpaca.clr._clr import AST

class Instance():
    def __init__(self, name: str, type: Type, context: Context, ast: AST):
        self.name = name
        self.type = type
        self.context = context
        self.ast = ast

    def __str__(self) -> str:
        return f"{self.name}{self.type}"
