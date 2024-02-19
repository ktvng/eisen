from __future__ import annotations

from alpaca.utils import Visitor
from eisen.state.basestate import BaseState
import eisen.adapters as adapters
from eisen.typecheck.typeparser import TypeParser

State = BaseState
class DefinitionVisitor(Visitor):
    def run(self, state: State):
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
    def struct_(fn, state: State) -> None:
        type_parser = TypeParser()
        node = adapters.Struct(state)
        state.get_type_factory().define_struct_type(
            struct_name=node.get_name(),
            namespace=state.get_enclosing_module().get_namespace_str(),
            attribute_names=node.get_child_attribute_names(),
            attribute_types=[type_parser.run(state.but_with(ast=ast))
                             for ast in node.get_child_attribute_asts()])

    @Visitor.for_ast_types("trait")
    def trait_(fn, state: State):
        node = adapters.Trait(state)
        type_parser = TypeParser()
        state.get_type_factory().define_trait_type(
            trait_name=node.get_name(),
            namespace=state.get_enclosing_module().get_namespace_str(),
            attribute_names=node.get_child_attribute_names(),
            attribute_types=[type_parser.run(state.but_with(ast=ast))
                             for ast in node.get_child_attribute_asts()])

    @Visitor.for_default
    def default_(fn, _: State) -> None:
        # nothing to do by default
        return
