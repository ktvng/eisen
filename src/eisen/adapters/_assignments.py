from __future__ import annotations

from alpaca.concepts import Type
from eisen.adapters.nodeinterface import AbstractNodeInterface
from eisen.adapters._refs import RefLike, Ref, Scope

class CompoundAssignment(AbstractNodeInterface):
    ast_types = ["+=", "-=", "*=", "/="]
    examples = """
    (+= (ref a) 4)
    (-= (. (ref b) c) (+ 4 9))
    """
    def get_arithmetic_operation(self) -> str:
        return self.state.get_ast().type[0]

class Assignment(AbstractNodeInterface):
    ast_type = "="
    examples = """
    1. single assignment
        (= (ref name) 4)
    2. multiple assignment
        (= (lvals (ref name1) (ref name2)) (tuple 4 4))
    3. multiple call assignment
        (= (lvals (ref name1) (ref name2)) (call ...))
    """

    def is_single_assignment(self) -> bool:
        return AbstractNodeInterface.first_child_is_token(self) or self.first_child().type != "lvals"

    def get_names_of_parent_objects(self):
        if self.first_child().type == "ref":
            return [Ref(self.state.but_with_first_child()).get_name()]
        if self.first_child().type == "lvals":
            return [RefLike(self.state.but_with(ast=child)).get_name()
                for child in self.first_child()]
        if self.first_child().type == ".":
            return [Scope(self.state).get_object_name()]

    def get_assigned_types(self) -> list[Type]:
        if self.first_child().type == "lvals":
            return [self.state.but_with(ast=child).get_returned_type()
                for child in self.first_child()]
        return [self.state.but_with(ast=self.first_child()).get_returned_type()]
