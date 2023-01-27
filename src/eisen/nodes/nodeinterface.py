from __future__ import annotations

from alpaca.clr import CLRToken
from alpaca.concepts import Type
from eisen.common.state import State

class AbstractNodeInterface():
    def __init__(self, state: State):
        self.state = state

    def first_child(self):
        return self.state.first_child()

    def second_child(self):
        return self.state.get_asl().second()

    def third_child(self):
        return self.state.get_asl().third()

    def get_line_number(self) -> int:
        return self.state.get_asl().line_number

    def get_node_type(self) -> str:
        return self.state.get_asl().type

    def get_name_from_first_child(self) -> str:
        """assumes the first child is a token containing the name"""
        return self.state.first_child().value

    def first_child_is_token(self) -> bool:
        """true if the first child is a CLRToken"""
        return isinstance(self.first_child(), CLRToken)

    def get_type_for_node_that_defines_a_type(self) ->Type:
        """returns the type for either a struct/interface node which defines a type."""
        return self.state.get_enclosing_module().get_defined_type(self._get_name())
