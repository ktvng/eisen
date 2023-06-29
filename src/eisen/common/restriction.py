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

    def get_name(self) -> str:
        return ""

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return str(type(self))

class NoRestriction(GeneralRestriction):
    def is_unrestricted(self) -> bool:
        return True

class VarRestriction(GeneralRestriction):
    def is_var(self) -> bool:
        return True

    def get_name(self) -> str:
        return "var"

class NullableVarRestriction(VarRestriction):
    def is_nullable(self) -> bool:
        return True

    def get_name(self) -> str:
        return "var?"

class LetRestriction(GeneralRestriction):
    def is_let(self) -> bool:
        return True

    def get_name(self) -> str:
        return "let"

class LetConstruction(LetRestriction):
    def is_let_construction(self) -> bool:
        return True

class ValRestriction(GeneralRestriction):
    def is_val(self) -> bool:
        return True

    def get_name(self) -> str:
        return "val"

class LiteralRestriction(GeneralRestriction):
    def is_literal(self) -> bool:
        return True

class FunctionalRestriction(GeneralRestriction):
    def is_functional(self) -> bool:
        return True

class PrimitiveRestriction(GeneralRestriction):
    def is_primitive(self) -> bool:
        return True
