from __future__ import annotations

from alpaca.concepts import AbstractRestriction

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

class PrimitiveRestriction(GeneralRestriction):
    def is_primitive(self) -> bool:
        return True
