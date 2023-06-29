from __future__ import annotations

from alpaca.concepts import InstanceState, Type
from eisen.common.initialization import Initializations

from eisen.common.restriction import GeneralRestriction, NoRestriction

class UsageStatus(InstanceState):
    def __init__(self,
            name: str,
            restriction: GeneralRestriction,
            initialization: Initializations):
        self.name = name
        self.restriction = restriction
        self.initialization = initialization
        self.attribute_initializations: dict[str, Initializations] = {}
        self._type = None

    def assignable_to(self, other: UsageStatus):
        return self.restriction.assignable_to(other.restriction, self.initialization)

    def mark_as_initialized(self, attribute_name=""):
        if attribute_name:
            self.mark_attribute_as_initialized(attribute_name)
        else:
            self.initialization = Initializations.Initialized

    def mark_as_underconstruction(self, type: Type):
        self._type = type
        self.initialization = Initializations.UnderConstruction

    def get_initialization_of_attribute(self, name: str) -> Initializations:
        return self.attribute_initializations.get(name, Initializations.NotInitialized)

    def mark_attribute_as_initialized(self, name: str):
        self.attribute_initializations[name] = Initializations.Initialized
        if len(self.attribute_initializations) == len(self._type.get_all_component_names()):
            self.initialization = Initializations.Initialized

    def is_under_construction(self) -> bool:
        return self.initialization == Initializations.UnderConstruction

    def is_anonymous(self) -> bool:
        return self.name == ""

    @staticmethod
    def anonymous(restriction: GeneralRestriction, init: Initializations) -> UsageStatus:
        return UsageStatus("", restriction, init)

    @staticmethod
    def abort():
        return UsageStatus("__abort__", None, None)

    @staticmethod
    def no_restriction() -> UsageStatus:
        return UsageStatus("", NoRestriction(), Initializations.Initialized)

    def is_aborted_status(self) -> bool:
        return self.name == "__abort__" and self.restriction is None and self.initialization is None

    def __str__(self) -> str:
        return str(self.restriction) + " " + ("notinit" if self.initialization == Initializations.NotInitialized else "init")

class AnonymousInstanceStatus(UsageStatus):
    def __init__(self, restriction: GeneralRestriction, initialzation: Initializations):
        super().__init__("", restriction, initialzation)
