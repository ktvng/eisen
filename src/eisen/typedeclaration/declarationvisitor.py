from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.concepts import Type, TypeFactory
from eisen.state.basestate import BaseState
import eisen.adapters as adapters

State = BaseState
class DeclarationVisitor(Visitor):
    """parses (struct ...) and (interface ...) asts into a instances of the
    proto_struct/proto_interface type, respectively,  which represents the
    declaration of the type without the actual definition.

    see FinalizationVisitor for more details.
    """

    def run(self, state: BaseState):
        self.apply(state)
        return state

    def apply(self, state: State) -> None:
        new_type: Type | None = self._route(state.get_ast(), state)
        if new_type is not None:
            state.get_enclosing_module().add_defined_type(new_type.name, new_type)

    @Visitor.for_ast_types("start")
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_ast_types("mod")
    def mod_(fn, state: State):
        adapters.Mod(state).enter_module_and_apply(fn)

    @Visitor.for_ast_types("struct")
    def struct_(fn, state: State) -> Type:
        return TypeFactory.produce_proto_struct_type(
            name=adapters.Struct(state).get_name(),
            mod=state.get_enclosing_module())

    @Visitor.for_ast_types("trait")
    def trait_(fn, state: State) -> Type:
        return TypeFactory.produce_proto_trait_type(
            name=adapters.Trait(state).get_name(),
            mod=state.get_enclosing_module())

    @Visitor.for_default
    def default_(fn, state: State):
        # nothing to do by default
        return

class DeclarationVisitor2(Visitor):
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
