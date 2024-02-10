from __future__ import annotations

from alpaca.concepts import Type
from eisen.adapters.nodeinterface import AbstractNodeInterface
from eisen.common.restriction import NewLetRestriction
from eisen.typecheck.typeparser import TypeParser, TypeFactory

class NewVec(AbstractNodeInterface):
    ast_type = "new_vec"
    examples = """
    (new_vec (type int))
    """

    def get_type(self) -> Type:
        return TypeFactory.produce_parametric_type(
            name="vec",
            parametrics=[TypeParser().apply(self.state.but_with_first_child())]) \
                .with_restriction(NewLetRestriction())
