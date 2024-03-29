from __future__ import annotations

from dataclasses import dataclass

from alpaca.concepts import InstanceState, Type, AbstractException
from eisen.common.initialization import Initializations

from eisen.common.restriction import (GeneralRestriction, NoRestriction, ImmutableRestriction, MutableRestriction, NilableRestriction,
                                      NewLetRestriction, LetRestriction, LiteralRestriction, PrimitiveRestriction,
                                      MoveRestriction)
from eisen.common.exceptions import Exceptions


class UsageStatus(InstanceState):
    def __init__(self,
            name: str,
            restriction: GeneralRestriction,
            initialization: Initializations,
            modifies_val_state: bool = False):
        self.name = name
        self.restriction = restriction
        self.initialization = initialization
        self._modifies_val_state = modifies_val_state
        self.attribute_initializations: dict[str, Initializations] = {}
        self._type = None

    def assignable_to(self, other: UsageStatus) -> AssignmentResult:
        return AssignmentResult.success()

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

    def is_initialized(self) -> bool:
        return self.initialization == Initializations.Initialized

    def is_under_construction(self) -> bool:
        return self.initialization == Initializations.UnderConstruction

    def is_anonymous(self) -> bool:
        return self.name == ""

    def is_unrestricted(self) -> bool:
        return False

    def modifies_val_state(self) -> bool:
        return self._modifies_val_state

    def is_mutable(self) -> bool:
        return False

    def is_immutable(self) -> bool:
        return False

    def is_move(self) -> bool:
        return False

    def is_let(self) -> bool:
        return False

    def is_let_construction(self) -> bool:
        return False

    def is_functional(self) -> bool:
        return False

    def is_nilable(self) -> bool:
        return False

    def is_literal(self) -> bool:
        return False

    def is_primitive(self) -> bool:
        return False

    def __str__(self) -> str:
        return self.name + "." + str(type(self)) + " = " + self.initialization


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


@dataclass
class AssignmentResult:
    ex_type: AbstractException | None = None
    msg: str | None = None

    @staticmethod
    def success():
        return AssignmentResult()

    def failed(self):
        return self.ex_type != None

class UnrestrictedStatus(UsageStatus):
    def is_unrestricted(self) -> bool:
        return True

class MutableStatus(UsageStatus):
    def is_mutable(self) -> bool:
        return True

    def assignable_to(self, other: UsageStatus):
        # if other.is_let_construction():
        #     return AssignmentResult(
        #         ex_type=Exceptions.LetInitializationMismatch,
        #         msg=f"'{self.name}' is declared as 'var', and cannot accept a new object (use let instead)")
        if other.is_literal():
            return AssignmentResult(
                ex_type=Exceptions.VarImproperAssignment,
                msg=f"'{self.name}' is declared as 'var', but is being assigned to a literal")
        if other.is_immutable():
            return AssignmentResult(
                ex_type=Exceptions.VarImproperAssignment,
                msg=f"'{other.name}' is 'val' cannot be assigned to a 'var' type")
        return AssignmentResult.success()

class NilableStatus(UsageStatus):
    def is_nilable(self) -> bool:
        return True

    def assignable_to(self, other: UsageStatus):
        if other.is_literal():
            return AssignmentResult(
                ex_type=Exceptions.VarImproperAssignment,
                msg=f"'{self.name}' is declared as 'var', but is being assigned to a literal")
        return AssignmentResult.success()

class LetStatus(UsageStatus):
    def is_let(self) -> bool:
        return True

    def assignable_to(self, other: UsageStatus):
        if self.is_initialized():
            return AssignmentResult(
                ex_type=Exceptions.LetReassignment,
                msg=f"'{self.name} is declared as 'let' and initialized; '{self.name}' cannot be reassigned")
        if not other.is_let_construction():
            return AssignmentResult(
                ex_type=Exceptions.LetInitializationMismatch,
                msg=f"'{self.name}' is declared as 'let', and must be constructed by a function")
        return AssignmentResult.success()

class NewLetStatus(UsageStatus):
    def is_let_construction(self) -> bool:
        return True

class ImmutableStatus(UsageStatus):
    def is_immutable(self) -> bool:
        return True

    def assignable_to(self, other: UsageStatus):
        # if other.is_let_construction():
        #     return AssignmentResult(
        #         ex_type=Exceptions.LetInitializationMismatch,
        #         msg=f"'{self.name}' is declared as 'var', and cannot accept a new object (use let instead)")

        if not self.is_initialized():
            return AssignmentResult.success()

        if other.is_literal():
            return AssignmentResult(
                ex_type=Exceptions.ImmutableVal,
                msg=f"'{self.name}' is declared as 'var', but is being assigned to a literal")
        if other.is_mutable():
            print(self)
            print(other)
            return AssignmentResult(
                ex_type=Exceptions.ImmutableVal,
                msg=f"'{self.name}' is 'val' cannot be assigned to a '{other.name}' which is 'var' type")

        return AssignmentResult.success()

class LiteralStatus(UsageStatus):
    def is_literal(self) -> bool:
        return True

class MoveStatus(UsageStatus):
    def is_move(self) -> bool:
        return True

    def assignable_to(self, other: UsageStatus):
        if other.is_let():
            return AssignmentResult.success()
        return AssignmentResult(
            ex_type=Exceptions.Move,
            msg=f"{other.name} must be declared as let")


class PrimitiveStatus(UsageStatus):
    def is_primitive(self) -> bool:
        return True

    def assignable_to(self, other: UsageStatus):
        if other.is_primitive() or other.is_literal() or other.is_unrestricted():
            return AssignmentResult.success()
        return AssignmentResult(
            ex_type=Exceptions.PrimitiveAssignmentMismatch,
            msg=f"'{self.name}' is a primitive")

class UsageStatusFactory():
    restriction_to_status_map = {
        hash(NoRestriction()): UnrestrictedStatus,
        hash(MutableRestriction()): MutableStatus,
        hash(ImmutableRestriction()): ImmutableStatus,
        hash(NilableRestriction()): NilableStatus,
        hash(LetRestriction()): LetStatus,
        hash(NewLetRestriction()): NewLetStatus,
        hash(LiteralRestriction()): LiteralStatus,
        hash(PrimitiveRestriction()): PrimitiveStatus,
        hash(MoveRestriction()): MoveStatus
    }

    @staticmethod
    def create(name: str, restriction: GeneralRestriction, initialization: Initializations = Initializations.NotInitialized,
               modifies_val_state = False):
        return UsageStatusFactory.restriction_to_status_map[hash(restriction)](name, restriction, initialization, modifies_val_state)

    @staticmethod
    def create_anonymous(restriction: GeneralRestriction, initialization: Initializations = Initializations.NotInitialized):
        return UsageStatusFactory.restriction_to_status_map[hash(restriction)]("", restriction, initialization, False)
