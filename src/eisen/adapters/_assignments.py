from __future__ import annotations

from eisen.adapters.nodeinterface import AbstractNodeInterface
from eisen.adapters._refs import RefLike, Ref, Scope

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

    def get_names_of_parent_objects(self):
        if self.first_child().type == "ref":
            return [Ref(self.state.but_with_first_child()).get_name()]
        if self.first_child().type == "lvals":
            return [RefLike(self.state.but_with(ast=child)).get_name()
                for child in self.first_child()]
        if self.first_child().type == ".":
            return [Scope(self.state).get_object_name()]
