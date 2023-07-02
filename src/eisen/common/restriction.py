from __future__ import annotations

from alpaca.concepts import AbstractRestriction

class GeneralRestriction(AbstractRestriction):
    def is_unrestricted(self) -> bool:
        return False

    def is_mutable(self) -> bool:
        return False

    def is_immutable(self) -> bool:
        return False

    def is_let(self) -> bool:
        return False

    def is_new_let(self) -> bool:
        return False

    def is_nilable(self) -> bool:
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

class MutableRestriction(GeneralRestriction):
    def is_mutable(self) -> bool:
        return True

    def get_name(self) -> str:
        return "mut"

class NilableRestriction(MutableRestriction):
    def is_nilable(self) -> bool:
        return True

    def get_name(self) -> str:
        return "nil?"

class LetRestriction(GeneralRestriction):
    def is_let(self) -> bool:
        return True

    def get_name(self) -> str:
        return "let"

class NewLetRestriction(LetRestriction):
    def is_new_let(self) -> bool:
        return True

class ImmutableRestriction(GeneralRestriction):
    def is_immutable(self) -> bool:
        return True

    def get_name(self) -> str:
        return "val"

class LiteralRestriction(GeneralRestriction):
    def is_literal(self) -> bool:
        return True

class PrimitiveRestriction(GeneralRestriction):
    def is_primitive(self) -> bool:
        return True
