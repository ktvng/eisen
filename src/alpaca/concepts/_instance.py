from __future__ import annotations

from alpaca.concepts._typeclass import TypeClass
from alpaca.concepts._context import Context 
from alpaca.clr._clr import CLRList

class Instance():
    def __init__(self, name: str, typeclass: TypeClass, context: Context, asl: CLRList):
        self.name = name
        self.type = typeclass
        self.context = context
        self.asl = asl

    def __str__(self) -> str:
        return f"{self.name}{self.type}"
        