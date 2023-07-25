from __future__ import annotations

from alpaca.clr import AST
from alpaca.concepts import Type
from eisen.adapters.nodeinterface import AbstractNodeInterface
from eisen.common import implemented_primitive_types
from eisen.common.restriction import (GeneralRestriction, LetRestriction,
                                      MutableRestriction, NilableRestriction, ImmutableRestriction,
                                      NewLetRestriction, PrimitiveRestriction, MoveRestriction)
from eisen.state.state_posttypecheck import State_PostTypeCheck

class _SharedMixins():
    def is_single_assignment(self) -> bool:
        return AbstractNodeInterface.first_child_is_token(self)

    def get_names(self) -> list[str]:
        match self.is_single_assignment():
            case True: return [self.first_child().value]
            case False: return [child.value for child in self.first_child()]

    def get_is_let(self) -> bool:
        match self.get_node_type():
            case "let": return True
            case "ilet": return True
            case _: return False

class TypeLike(AbstractNodeInterface):
    ast_types = ["type", "mut_type", "nilable_type", "new_type", "move_type"]
    examples = """
    (type name)
    (var_type name)
    """
    get_name = AbstractNodeInterface.get_name_from_first_child

    def get_restriction(self) -> GeneralRestriction:
        if self.get_node_type() == "fn_type":
            return ImmutableRestriction()
        if self.state.get_ast().first().value in implemented_primitive_types:
            return PrimitiveRestriction()

        match self.get_node_type():
            case "mut_type": return MutableRestriction()
            case "type": return ImmutableRestriction()
            case "nilable_type": return NilableRestriction()
            case "new_type": return NewLetRestriction()
            case "move_type": return MoveRestriction()
            case _: raise Exception(f"get_restriction not implemented for {self.state.get_ast()}")

    def get_is_nilable(self) -> bool:
        return self.get_node_type() == "nilable_type"

class InferenceAssign(AbstractNodeInterface, _SharedMixins):
    ast_types = ["ilet", "imut", "ival", "inil?"]
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

    @staticmethod
    def map_ilet_restrictions(r: GeneralRestriction) -> GeneralRestriction:
        match r:
            case NewLetRestriction(): return LetRestriction()
            case _: return r

    @staticmethod
    def get_hint_restrictions(hint: Type) -> GeneralRestriction:
        if hint.is_tuple():
            return [InferenceAssign.map_ilet_restrictions(_type.restriction) for _type in hint.unpack_into_parts()]
        return InferenceAssign.map_ilet_restrictions(hint.restriction)


    def assigns_a_tuple(self) -> bool:
        return isinstance(self.first_child(), AST)

    def get_is_nilable(self) -> bool:
        match self.get_node_type():
            case "inil?": return True
            case _: return False

    def get_restriction(self, hint: Type) -> GeneralRestriction:
        match self.get_node_type():
            case "ilet": return InferenceAssign.get_hint_restrictions(hint)
            case "inil?": return NilableRestriction()
            case "ival": return ImmutableRestriction()
            case "ivar": return MutableRestriction()
            case _: raise Exception(f"get_restriction unhandled for {self.get_node_type()}")

    def get_assigned_types(self) -> list[Type]:
        if not isinstance(self.state, State_PostTypeCheck):
            raise Exception("this method can only be called after typechecker is run")
        return self.state.get_returned_type().unpack_into_parts()

class Colon(AbstractNodeInterface):
    ast_types = [":"]
    examples = """
    (: name (type type_name))
    """

    def get_name(self) -> str:
        return self.first_child().value

    def is_let(self) -> bool:
        return (self.state.get_returned_type().restriction.is_let() or
                self.state.get_returned_type().restriction.is_new_let())

class Typing(AbstractNodeInterface, _SharedMixins):
    ast_types = ["let", "mut", "val", "nil?", ":"]
    examples = """
    1. multiple assignment
        (ast_TYPE (tags ...) (type ...))
    2. single_assignment
        (ast_TYPE name (type ...))
    """
    def get_restriction(self) -> GeneralRestriction:
        match self.get_node_type():
            case ":": return TypeLike(self.state.but_with_second_child()).get_restriction()
            case _: return Decl(self.state).get_restriction()

    def get_is_nilable(self) -> bool:
        match self.get_node_type():
            case ":": return TypeLike(self.state.but_with_second_child()).get_is_nilable()
            case _: return Decl(self.state).get_is_nilable()

    def get_type_ast(self) -> AST:
        return self.second_child()

class Decl(AbstractNodeInterface, _SharedMixins):
    ast_types = ["let", "mut", "val", "nil?"]
    examples = """
    1. multiple assignment
        (ast_TYPE (tags ...) (type ...))
    2. single_assignment
        (ast_TYPE name (type ...))
    """
    def _is_primitive(self) -> bool:
        return TypeLike(self.state.but_with_second_child()).get_restriction().is_primitive()

    def get_restriction(self) -> GeneralRestriction:
        match self.get_node_type():
            case "let": return PrimitiveRestriction() if self._is_primitive() else LetRestriction()
            case "mut": return MutableRestriction()
            case "val": return ImmutableRestriction()
            case "nil?": return NilableRestriction()
            case _: raise Exception(f"not implemented for {self.get_node_type()} {self.state.get_ast()}")

    def get_is_nilable(self) -> bool:
        return self.get_node_type() == "nil?"

    def get_spread_values(self) -> set[int]:
        # let nodes are locally declared and therefore have local depth
        if self.get_node_type() == "let":
            return {self.state.depth}

        # all other nodes are pointers and have no initial spread
        return set()
