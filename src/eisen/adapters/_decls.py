from __future__ import annotations

from alpaca.clr import CLRList
from alpaca.concepts import Type
from eisen.adapters.nodeinterface import AbstractNodeInterface
from eisen.common import implemented_primitive_types
from eisen.common.restriction import (GeneralRestriction, LetRestriction,
                                      MutableRestriction, NilableRestriction, ImmutableRestriction,
                                      NewLetRestriction, PrimitiveRestriction)
class _SharedMixins():
    def is_single_assignment(self) -> bool:
        return AbstractNodeInterface.first_child_is_token(self)

    def get_names(self) -> list[str]:
        match self.is_single_assignment():
            case True: return [self.first_child().value]
            case False: return [child.value for child in self.first_child()]

class TypeLike(AbstractNodeInterface):
    asl_types = ["type", "mut_type", "nilable_type", "new_type"]
    examples = """
    (type name)
    (var_type name)
    """
    get_name = AbstractNodeInterface.get_name_from_first_child

    def get_restriction(self) -> GeneralRestriction:
        if self.get_node_type() == "fn_type":
            return ImmutableRestriction()
        if self.state.get_asl().first().value in implemented_primitive_types:
            return PrimitiveRestriction()

        match self.get_node_type():
            case "mut_type": return MutableRestriction()
            case "type": return ImmutableRestriction()
            case "nilable_type": return NilableRestriction()
            case "new_type": return NewLetRestriction()
            case _: raise Exception(f"get_restriction not implemented for {self.state.get_asl()}")

    def get_is_nilable(self) -> bool:
        return self.get_node_type() == "nilable_type"

class InferenceAssign(AbstractNodeInterface, _SharedMixins):
    asl_types = ["ilet", "imut", "ival", "inil?"]
    examples = """
    1. (ilet name (call ...))
    2. (ilet name 4)
    3. (ilet name (<expression>))
    4. (ilet (tags ...) (tuple ...))
    5. (ilet (tags ...) (call ...))
    """
    def hint_is_primitive(self, hint: Type) -> bool:
        if hint.is_tuple():
            return hint.components[0].restriction.is_primitive()
        return hint.restriction.is_primitive()

    def get_hint_restriction(self, hint: Type) -> GeneralRestriction:
        # TODO: fix this logic. How do we infer multiple types when a function could
        # return multiple restrictions??
        if self.hint_is_primitive(hint):
            return PrimitiveRestriction()

        if not hint.is_tuple() and hint.restriction.is_new_let():
            return LetRestriction()
        return hint.restriction

    def assigns_a_tuple(self) -> bool:
        return isinstance(self.first_child(), CLRList)

    def get_is_nilable(self) -> bool:
        match self.get_node_type():
            case "inil?": return True
            case _: return False

    def get_restriction(self, hint: Type) -> GeneralRestriction:
        match self.get_node_type():
            case "ilet": return self.get_hint_restriction(hint)
            case "inil?": return NilableRestriction()
            case "ival": return ImmutableRestriction()
            case "ivar": return MutableRestriction()
            case _: raise Exception(f"get_restriction unhandled for {self.get_node_type()}")

class Typing(AbstractNodeInterface, _SharedMixins):
    asl_types = ["let", "mut", "val", "nil?", ":"]
    examples = """
    1. multiple assignment
        (ASL_TYPE (tags ...) (type ...))
    2. single_assignment
        (ASL_TYPE name (type ...))
    """
    def get_restriction(self) -> GeneralRestriction:
        match self.get_node_type():
            case ":": return TypeLike(self.state.but_with_second_child()).get_restriction()
            case _: return Decl(self.state).get_restriction()

    def get_is_nilable(self) -> bool:
        match self.get_node_type():
            case ":": return TypeLike(self.state.but_with_second_child()).get_is_nilable()
            case _: return Decl(self.state).get_is_nilable()

    def get_type_asl(self) -> CLRList:
        return self.second_child()

class Decl(AbstractNodeInterface, _SharedMixins):
    asl_types = ["let", "mut", "val", "nil?"]
    examples = """
    1. multiple assignment
        (ASL_TYPE (tags ...) (type ...))
    2. single_assignment
        (ASL_TYPE name (type ...))
    """
    def _is_primitive(self) -> bool:
        return TypeLike(self.state.but_with_second_child()).get_restriction().is_primitive()

    def get_restriction(self) -> GeneralRestriction:
        match self.get_node_type():
            case "let": return PrimitiveRestriction() if self._is_primitive() else LetRestriction()
            case "mut": return MutableRestriction()
            case "val": return ImmutableRestriction()
            case "nil?": return NilableRestriction()
            case _: raise Exception(f"not implemented for {self.get_node_type()} {self.state.asl}")

    def get_is_nilable(self) -> bool:
        return self.get_node_type() == "nil?"

    def get_spread_values(self) -> set[int]:
        # let nodes are locally declared and therefore have local depth
        if self.get_node_type() == "let":
            return {self.state.depth}

        # all other nodes are pointers and have no initial spread
        return set()
