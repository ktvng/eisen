from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.concepts import Type, TypeFactory
from eisen.state.basestate import BaseState as State
import eisen.adapters as adapters

class DeclarationVisitor(Visitor):
    """parses (struct ...) and (interface ...) asts into a instances of the
    proto_struct/proto_interface type, respectively,  which represents the
    declaration of the type without the actual definition.

    see FinalizationVisitor for more details.
    """

    def run(self, state: State):
        self.apply(state)
        return state

    def apply(self, state: State) -> None:
        return self._route(state.get_ast(), state)

    def adds_type_to_module(f):
        """adds the returned type to the list of known typesclasses in
        the enclosing module"""
        def decorator(fn, state: State) -> None:
            result: Type = f(fn, state)
            state.get_enclosing_module().add_defined_type(result.name, result)
        return decorator

    @Visitor.for_ast_types("start")
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_ast_types("mod")
    def mod_(fn, state: State):
        adapters.Mod(state).enter_module_and_apply(fn)

    @Visitor.for_ast_types("struct")
    @adds_type_to_module
    def struct_(fn, state: State) -> Type:
        return TypeFactory.produce_proto_struct_type(
            name=adapters.Struct(state).get_struct_name(),
            mod=state.get_enclosing_module())

    @Visitor.for_ast_types("interface")
    @adds_type_to_module
    def interface_(fn, state: State) -> Type:
        return TypeFactory.produce_proto_interface_type(
            name=adapters.Interface(state).get_interface_name(),
            mod=state.get_enclosing_module())

    @Visitor.for_ast_types("variant")
    @adds_type_to_module
    def variant_(fn, state: State) -> Type:
        return TypeFactory.produce_proto_variant_type(
            name=adapters.Variant(state).get_variant_name(),
            mod=state.get_enclosing_module())

    @Visitor.for_default
    def default_(fn, state: State):
        # nothing to do by default
        return
