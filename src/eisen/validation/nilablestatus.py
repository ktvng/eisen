from __future__ import annotations

from alpaca.concepts import Type, Context
from eisen.common.restriction import GeneralRestriction

class NilableStatus():
    def __init__(self, name: str, is_nilable: bool, could_be_nil: bool = False):
        self.name = name
        self.is_nilable = is_nilable
        self.could_be_nil = could_be_nil

    def __str__(self) -> str:
        state = f"?-could_be_nil:{self.could_be_nil}" if self.is_nilable else ""
        return f"{self.name}{state}"

    def update(self, nilstate: NilableStatus) -> NilableStatus:
        return NilableStatus(self.name, self.is_nilable, nilstate.could_be_nil)

    def __hash__(self) -> int:
        return hash(self.name + str(self.is_nilable))

    @staticmethod
    def not_nil() -> NilableStatus:
        return NilableStatus("", True, False)

    @staticmethod
    def maybe_nil() -> NilableStatus:
        return NilableStatus("", True, True)

    @staticmethod
    def never_nil() -> NilableStatus:
        return NilableStatus("", False, False)

    @staticmethod
    def for_type(type: Type) -> NilableStatus:
        r: GeneralRestriction = type.restriction
        if r.is_nilable():
            return NilableStatus.maybe_nil()
        return NilableStatus.never_nil()

    def not_nil_in_all_contexts(self, contexts: list[Context]) -> bool:
        return all([context.get_nilstatus(self.name) and context.get_nilstatus(self.name).could_be_nil == False for context in contexts])

    def nil_in_some_context(self, contexts: list[Context]) -> bool:
        return not self.not_nil_in_all_contexts(contexts)
