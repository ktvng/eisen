from __future__ import annotations
from typing import TYPE_CHECKING

from alpaca.concepts import InstanceState
from eisen.common.initialization import Initializations

if TYPE_CHECKING:
    from eisen.common.restriction import GeneralRestriction

class EisenInstanceState(InstanceState):
    def __init__(self,
            name: str,
            restriction: GeneralRestriction,
            initialization: Initializations):
        self.name = name
        self.restriction = restriction
        self.initialization = initialization

    def assignable_to(self, other: EisenInstanceState):
        return self.restriction.assignable_to(other.restriction, self.initialization)

    def mark_as_initialized(self):
        self.initialization = Initializations.NotNull

    def __str__(self) -> str:
        return str(self.restriction) + " " + ("notinit" if self.initialization == Initializations.NotInitialized else "init")

class EisenAnonymousInstanceState(EisenInstanceState):
    def __init__(self, restriction: GeneralRestriction, initialzation: Initializations):
        super().__init__("", restriction, initialzation)
