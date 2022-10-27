from __future__ import annotations

class Restriction():
    var = "var"
    nullable_var = "nullable_var"
    val = "val"
    let = "let"
    none = "none"
    literal = "literal"
    let_primitive = "let_primitive"

    class States:
        possibly_null = "possibly_null"
        not_null = "not_null"
        initialized = "initialized"
        not_initialized = "not_initialized"
        none = "none"

    def __init__(self, type: str, state: str):
        self.type = type
        self.state = state

    @classmethod
    def create_var(cls) -> Restriction:
        return Restriction(cls.var, cls.States.not_initialized)

    @classmethod
    def create_let(cls, is_init: bool) -> Restriction:
        if is_init:
            return Restriction(cls.let, cls.States.initialized)
        return Restriction(cls.let, cls.States.not_initialized)

    @classmethod
    def create_literal(cls) -> Restriction:
        return Restriction(cls.literal, cls.States.none)

    @classmethod
    def create_none(cls) -> Restriction:
        return Restriction(cls.none, cls.States.none)

    @classmethod
    def for_let_of_novel_type(cls) -> Restriction:
        return Restriction(cls.let_primitive, cls.States.not_initialized)

    def allows_for_reassignment(self) -> bool:
        return (self.type == "var"
            or self.type == "let_primitve")

    def __str__(self) -> str:
        return f"{self.type}.{self.state}"

    def assignable_to(self, right: Restriction) -> tuple[bool, str]:
        assignable = False
        if self.type == Restriction.let_primitive:
            assignable = (right.type == Restriction.let_primitive 
                or right.type == Restriction.literal
                or right.type == Restriction.none)
            if not assignable:
                return False, ("a primitive type declared by 'let' can only be assigned to other "
                    "primitive types declared by 'let' or to other literals")
        return True, "success"

    