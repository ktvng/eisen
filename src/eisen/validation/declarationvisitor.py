from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.concepts import Type, TypeFactory
from eisen.common.state import State
import eisen.nodes as nodes

class DeclarationVisitor(Visitor):
    """parses (struct ...) and (interface ...) asls into a instances of the
    proto_struct/proto_interface type, respectively,  which represents the
    declaration of the type without the actual definition.

    see FinalizationVisitor for more details.
    """

    def apply(self, state: State) -> None:
        return self._route(state.get_asl(), state)

    def adds_type_to_module(f):
        """adds the returned type to the list of known typesclasses in
        the enclosing module"""
        def decorator(fn, state: State) -> None:
            result: Type = f(fn, state)
            state.add_defined_type(result)
        return decorator

    @Visitor.for_asls("start")
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_asls("mod")
    def mod_(fn, state: State):
        nodes.Mod(state).enter_module_and_apply(fn)

    @Visitor.for_asls("struct")
    @adds_type_to_module
    def struct_(fn, state: State) -> Type:
        return TypeFactory.produce_proto_struct_type(
            name=nodes.Struct(state).get_struct_name(),
            mod=state.get_enclosing_module())

    @Visitor.for_asls("interface")
    @adds_type_to_module
    def interface_(fn, state: State) -> Type:
        return TypeFactory.produce_proto_interface_type(
            name=nodes.Interface(state).get_interface_name(),
            mod=state.get_enclosing_module())

    @Visitor.for_asls("variant")
    @adds_type_to_module
    def variant_(fn, state: State) -> Type:
        return TypeFactory.produce_proto_variant_type(
            name=nodes.Variant(state).get_variant_name(),
            mod=state.get_enclosing_module())

    @Visitor.for_default
    def default_(fn, state: State):
        # nothing to do by default
        return
