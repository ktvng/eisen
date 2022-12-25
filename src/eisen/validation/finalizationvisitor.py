from __future__ import annotations

from alpaca.utils import Visitor
from eisen.common.state import State
from eisen.validation.nodetypes import Nodes
from eisen.validation.typeparser import TypeParser
from eisen.validation.validate import Validate

class InterfaceFinalizationVisitor(Visitor):
    """this finalizes a proto_interface into an interface type.
    we need to separate declaration and definition because types may refer back to
    themselves, or to other types which have yet to be defined, but exist in the 
    same module.
    """
    def apply(self, state: State) -> None:
        return self._route(state.get_asl(), state)

    @Visitor.for_asls("start")
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_asls("mod")
    def mod_(fn, state: State):
        Nodes.Mod(state).enter_module_and_apply_fn_to_child_asls(fn)

    @Visitor.for_asls("interface")
    def interface_(fn, state: State) -> None:
        node = Nodes.Interface(state)
        this_interface_type = node.get_this_type()
        
        # TODO: consider whether or not to allow interfaces to inherit from other interfaces
        this_interface_type.finalize(
            components=[TypeParser().apply(state.but_with(asl=child)) 
                for child in node.get_child_attribute_asls()],
            component_names=node.get_child_attribute_names(),
            inherits=[])

    @Visitor.for_default
    def default_(fn, state: State) -> None:
        # nothing to do by default
        return


class StructFinalizationVisitor(Visitor):
    """finalization but for structs. see InterfaceFinalizationVisitor for details"""
    def apply(self, state: State) -> None:
        return self._route(state.get_asl(), state)

    @Visitor.for_asls("start")
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_asls("mod")
    def mod_(fn, state: State):
        Nodes.Mod(state).enter_module_and_apply_fn_to_child_asls(fn)
 
    @Visitor.for_asls("struct")
    def struct_(fn, state: State) -> None:
        node = Nodes.Struct(state)
        this_struct_type = node.get_this_type()
        this_struct_type.finalize(
            components=[TypeParser().apply(state.but_with(asl=asl)) 
                for asl in node.get_child_attribute_asls()],
            component_names=node.get_child_attribute_names(),
            inherits=node.get_implemented_interfaces(),
            embeds=node.get_embedded_structs())

        # perform validations
        Validate.embeddings_dont_conflict(state, this_struct_type)
        Validate.all_implementations_are_complete(state, this_struct_type)

    @Visitor.for_default
    def default_(fn, state: State) -> None:
        # nothing to do by default
        return
    