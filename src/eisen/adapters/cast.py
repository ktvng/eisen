from __future__ import annotations

from alpaca.concepts import Type
from eisen.adapters.nodeinterface import AbstractNodeInterface

class Cast(AbstractNodeInterface):
    asl_type = "cast"
    examples = """
    (cast (ref obj) (type otherObj))
    """

    def get_cast_into_type(self) -> Type:
        return self.state.but_with_second_child().get_returned_type()
