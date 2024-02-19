from __future__ import annotations

from alpaca.concepts import Type
from eisen.adapters.nodeinterface import AbstractNodeInterface
from eisen.common.restriction import NewLetRestriction

class NewVec(AbstractNodeInterface):
    ast_type = "new_vec"
    examples = """
    (new_vec (type int))
    """

    def get_type(self) -> Type:
        # TODO: broken after new types
        return TypeFactory.produce_parametric_type(
            name="vec",
            parametrics=[TypeParser().apply(self.state.but_with_first_child())]) \
                .with_restriction(NewLetRestriction())
