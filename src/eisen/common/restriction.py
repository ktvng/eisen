from __future__ import annotations

from alpaca.concepts import AbstractRestriction, InstanceState, Initialization

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

class EisenAnonymousInstanceState(EisenInstanceState):
    def __init__(self, restriction: AbstractRestriction, initialzation: Initializations):
        super().__init__("", restriction, initialzation)

class GeneralRestriction(AbstractRestriction):
    def is_unrestricted(self) -> bool:
        return False

    def is_var(self) -> bool:
        return False

    def is_val(self) -> bool:
        return False

    def is_let(self) -> bool:
        return False

    def is_nullable(self) -> bool:
        return False

    def is_literal(self) -> bool:
        return False

    def is_primitive(self) -> bool:
        return False

    def allows_for_reassignment(self) -> bool:
        return False

    def assignable_to(self, other: GeneralRestriction, current_init_state: Initialization) -> bool:
        return False

class NoRestriction(GeneralRestriction):
    def allows_for_reassignment(self) -> bool:
        return True

    def assignable_to(self, other: GeneralRestriction, current_init_state: Initialization) -> bool:
        return True

    def is_unrestricted(self) -> bool:
        return True

class VarRestriction(GeneralRestriction):
    def is_var(self) -> bool:
        return True

    def allows_for_reassignment(self) -> bool:
        return True

    # TODO: rename to assignable to
    def assignable_to(self, other: GeneralRestriction, current_init_state: Initialization) -> bool:
        return other.is_var() or other.is_let() or other.is_primitive()

class LetRestriction(GeneralRestriction):
    def is_let(self) -> bool:
        return True

    def assignable_to(self, other: GeneralRestriction, current_init_state: Initialization) -> bool:
        return (current_init_state == Initializations.NotInitialized) and (
            other.is_let() or other.is_unrestricted())

class ValRestriction(GeneralRestriction):
    def is_val(self) -> bool:
        return True

class LiteralRestriction(GeneralRestriction):
    def is_literal(self) -> bool:
        return True

class PrimitiveRestriction(GeneralRestriction):
    def is_primitive(self) -> bool:
        return True

    def allows_for_reassignment(self) -> bool:
        return True

    def assignable_to(self, other: GeneralRestriction, current_init_state: Initialization) -> bool:
        return other.is_primitive() or other.is_literal() or other.is_unrestricted() 

class Initializations(Initialization):
    PossiblyNull = "possiblynull"
    NotNull = "notnull"
    NotInitialized = "notinitialized"
    Initialized = "initialized"
    
    # def assignable_to(self, right: Restriction) -> tuple[bool, str]:
    #     # print(self, right)
    #     assignable = False
    #     if self.type == Restriction.let_primitive:
    #         assignable = (right.type == Restriction.let_primitive 
    #             or right.type == Restriction.literal
    #             or right.type == Restriction.none)
    #         if not assignable:
    #             return False, ("a primitive type declared by 'let' can only be assigned to other "
    #                 "primitive types declared by 'let' or to other literals")
    #         return True, "success"
    #     if self.type == Restriction.none:
    #         return True, "TODO: we should't be getting None here right?"
    #     if self.type == Restriction.var:
    #         assignable = (right.type == Restriction.var
    #             or right.type == Restriction.let
    #             or right.type == Restriction.let_primitive)
    #         if not assignable:
    #             return False, ("a type declared by 'var' can only be assigned to other "
    #                 "variable declared by 'var' or to memory declared with 'let'"
    #                 f"\nleft={self}\nright={right}")
    #         return True, "success"
    #     if self.type == Restriction.let:
    #         # TODO: none is added because restriction logic is not fully built out yet
    #         assignable = (self.state == Restriction.States.not_initialized and
    #             (right.type == Restriction.let or right.type == Restriction.none))
    #         if not assignable:
    #             return False, ("memory declared by 'let' cannot be reassigned after it has been "
    #                 "initialized the first time")
    #         return True, "success"

    #     raise Exception(f"{self} not implemented assignable_to")
