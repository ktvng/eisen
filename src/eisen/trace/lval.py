from __future__ import annotations

from eisen.trace.entity import Trait
from eisen.trace.memory import Memory

class Lval():
    def __init__(self, name: str, memory: Memory, trait: Trait) -> None:
        self.name = name
        self.memory = memory
        self.trait = trait
