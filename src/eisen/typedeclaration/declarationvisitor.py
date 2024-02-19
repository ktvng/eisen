from __future__ import annotations

from alpaca.utils import Visitor
from eisen.state.basestate import BaseState
import eisen.adapters as adapters

State = BaseState
class DeclarationVisitor(Visitor):
    def run(self, state: BaseState):
        self.apply(state)
        return state

    def apply(self, state: State) -> None:
        self._route(state.get_ast(), state)


    @Visitor.for_ast_types("start")
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_ast_types("mod")
    def mod_(fn, state: State):
        adapters.Mod(state).enter_module_and_apply(fn)

    @Visitor.for_ast_types("struct")
    def struct_(fn, state: State):
        return state.get_type_factory().declare_type(
            name=adapters.Struct(state).get_name(),
            namespace=state.get_enclosing_module().get_namespace_str())

    @Visitor.for_ast_types("trait")
    def trait_(fn, state: State):
        return state.get_type_factory().declare_type(
            name=adapters.Trait(state).get_name(),
            namespace=state.get_enclosing_module().get_namespace_str())

    @Visitor.for_default
    def default_(fn, _: State):
        # nothing to do by default
        return
