from __future__ import annotations

class GeneralRestriction():
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

    def is_move(self) -> bool:
        return False

    def get_name(self) -> str:
        return ""

    def is_new(self) -> bool: return False
    def is_var(self) -> bool: return False
    def is_mut(self) -> bool: return False
    def is_mut_star(self) -> bool: return False
    def is_move(self) -> bool: return False
    def is_void(self) -> bool: return False
    def is_data(self) -> bool: return False


    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return str(type(self))

class Bindings:
    """
    new - actual object allocation
    var - pointer
    mut - mutable pointer
    mut* - memory mutable pointer
    move - moved memory
    void - for tuples that need to get destructed
    data - for primitives and things that can get copied
    """

    class New:
        def is_new(self) -> bool: return True
        def is_nilable(self) -> bool: return False

    class Var:
        def is_var(self) -> bool: return True
        def is_nilable(self) -> bool: return False

    class Mut:
        def is_mut(self) -> bool: return True
        def is_nilable(self) -> bool: return False

    class MutStar:
        def is_mut_star(self) -> bool: return True
        def is_nilable(self) -> bool: return False

    class Move:
        def is_move(self) -> bool: return True
        def is_nilable(self) -> bool: return False

    class Void:
        def is_void(self) -> bool: return True
        def is_nilable(self) -> bool: return False

    class Data:
        def is_data(self) -> bool: return True
        def is_nilable(self) -> bool: return False



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

class MoveRestriction(GeneralRestriction):
    def is_move(self) -> bool:
        return True
