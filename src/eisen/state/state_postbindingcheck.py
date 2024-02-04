from __future__ import annotations

from alpaca.concepts import Type
from eisen.common.binding import CompositeBinding
from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor
from eisen.state.basestate import BaseState

class State_PostBindingCheck(State_PostInstanceVisitor):
    @staticmethod
    def create_from_basestate(state: BaseState):
        return State_PostBindingCheck(**state._get())

    def get_struct_binding(self, struct: Type) -> CompositeBinding:
        return self.struct_bindings[struct]
