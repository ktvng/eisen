from __future__ import annotations

from alpaca.concepts import AbstractRestriction, Type, TypeFactory
from eisen.common.initialization import Initializations

class RestrictionHelper:
    @staticmethod
    def process_type_returned_by_function(type: Type) -> Type:
        """
        If a 'let' object is returned by a function, it should be given the
        restriction of 'LetConstruction' as this is a function which constructs
        the object in place.

        :param type: The type returned by the function.
        :type type: Type
        :return: The same base type with correct restrictions.
        :rtype: Type
        """
        if type.is_tuple():
            return TypeFactory.produce_tuple_type(
                components=[comp.with_restriction(LetConstruction())
                    if comp.restriction.is_let()
                    else comp
                    for comp in type.components])

        elif type.restriction.is_let() or type.restriction.is_functional():
            return type.with_restriction(LetConstruction())
        return type


class RestrictionViolation:
    LetReassignment = 0
    LetInitializationToPointer = 1
    LetBadConstruction = 2

    VarAssignedToLiteral = 10
    VarNoNullableAssignment = 11
    VarAssignedToLetConstruction = 12

    PrimitiveToNonPrimitiveAssignment = 20

    FunctionalMisassigment = 30

    ValNoReassignment = 40

class GeneralRestriction(AbstractRestriction):
    def is_unrestricted(self) -> bool:
        return False

    def is_var(self) -> bool:
        return False

    def is_val(self) -> bool:
        return False

    def is_let(self) -> bool:
        return False

    def is_let_construction(self) -> bool:
        return False

    def is_functional(self) -> bool:
        return False

    def is_nullable(self) -> bool:
        return False

    def is_literal(self) -> bool:
        return False

    def is_primitive(self) -> bool:
        return False

    def allows_for_reassignment(self) -> bool:
        return False

    def assignable_to(self, other: GeneralRestriction, current_init_state: Initializations) -> bool:
        return False, None

    def get_name(self) -> str:
        return ""

    def __str__(self) -> str:
        return str(type(self))

class NoRestriction(GeneralRestriction):
    def allows_for_reassignment(self) -> bool:
        return True

    def assignable_to(self, other: GeneralRestriction, current_init_state: Initializations) -> bool:
        return True, None

    def is_unrestricted(self) -> bool:
        return True

class VarRestriction(GeneralRestriction):
    def is_var(self) -> bool:
        return True

    def allows_for_reassignment(self) -> bool:
        return True

    def get_name(self) -> str:
        return "var"

    def assignable_to(self, other: GeneralRestriction, current_init_state: Initializations) -> bool:
        if other.is_literal():
            return False, RestrictionViolation.VarAssignedToLiteral
        if other.is_nullable():
            return False, RestrictionViolation.VarNoNullableAssignment
        if other.is_let_construction():
            return False, RestrictionViolation.VarAssignedToLetConstruction
        return True, None

class NullableVarRestriction(VarRestriction):
    def is_nullable(self) -> bool:
        return True

    def get_name(self) -> str:
        return "var?"

    def assignable_to(self, other: GeneralRestriction, current_init_state: Initializations) -> bool:
        if other.is_literal():
            return False, RestrictionViolation.VarAssignedToLiteral
        return True, None

class LetRestriction(GeneralRestriction):
    def is_let(self) -> bool:
        return True

    def get_name(self) -> str:
        return "let"

    def assignable_to(self, other: GeneralRestriction, current_init_state: Initializations) -> bool:
        if current_init_state == Initializations.Initialized:
            return False, RestrictionViolation.LetReassignment
        if other.is_val() or other.is_var():
            return False, RestrictionViolation.LetInitializationToPointer
        if not other.is_let_construction():
            if other.is_functional():
                return True, None
            return False, RestrictionViolation.LetBadConstruction
        return True, None

class LetConstruction(LetRestriction):
    def is_let_construction(self) -> bool:
        return True

class ValRestriction(GeneralRestriction):
    def is_val(self) -> bool:
        return True

    def get_name(self) -> str:
        return "val"

    def assignable_to(self, other: GeneralRestriction, current_init_state: Initializations) -> bool:
        if current_init_state == Initializations.NotInitialized:
            return True, None
        return False, RestrictionViolation.ValNoReassignment

class LiteralRestriction(GeneralRestriction):
    def is_literal(self) -> bool:
        return True

class FunctionalRestriction(GeneralRestriction):
    def is_functional(self) -> bool:
        return True

    def assignable_to(self, other: GeneralRestriction, current_init_state: Initializations) -> bool:
        if other.is_functional():
            return True, None
        if other.is_let_construction():
            return True, None
        return False, RestrictionViolation.FunctionalMisassigment

class PrimitiveRestriction(GeneralRestriction):
    def is_primitive(self) -> bool:
        return True

    def allows_for_reassignment(self) -> bool:
        return True

    def assignable_to(self, other: GeneralRestriction, current_init_state: Initializations) -> bool:
        if other.is_primitive() or other.is_literal() or other.is_unrestricted():
            return True, None

        return False, RestrictionViolation.PrimitiveToNonPrimitiveAssignment
