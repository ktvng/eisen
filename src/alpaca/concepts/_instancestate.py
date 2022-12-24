from __future__ import annotations

from alpaca.concepts._typeclass import AbstractRestriction
from alpaca.concepts._initialization import Initialization

class InstanceState:
    def __init__(
            self, name: str, 
            restriction: AbstractRestriction, 
            initialization: Initialization) -> None:
        self.name = name
        self.restriction = restriction
        self.initialization = initialization
