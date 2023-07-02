from __future__ import annotations

from alpaca.concepts import Type
from eisen.adapters.nodeinterface import AbstractNodeInterface
from eisen.common import implemented_primitive_types
from eisen.common.restriction import (VarRestriction, GeneralRestriction, NullableVarRestriction,
    PrimitiveRestriction, ValRestriction)

class TypeLike(AbstractNodeInterface):
    asl_type = "type"
    examples = """
    (type name)
    (var_type name)
    """
    get_name = AbstractNodeInterface.get_name_from_first_child

    def get_restriction(self, type: Type) -> GeneralRestriction:
        # var takes precedence over primitive
        if self.get_node_type() == "var_type":
            return VarRestriction()
        elif self.get_node_type() == "var_type?":
            return NullableVarRestriction()

        if type.classification == Type.classifications.variant:
            return VarRestriction()

        if self.state.get_asl().first().value in implemented_primitive_types:
            restriction = PrimitiveRestriction()
        elif self.state.get_asl().type == "type":
            restriction = ValRestriction()
        return restriction
