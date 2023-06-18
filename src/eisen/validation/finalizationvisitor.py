from __future__ import annotations

from alpaca.utils import Visitor
from eisen.state.basestate import BaseState as State
import eisen.adapters as adapters
from eisen.validation.typeparser import TypeParser
from eisen.validation.validate import Validate


class FinalizationVisitor(Visitor):
    """this finalizes proto types into the fully built-out type.
    we need to separate declaration and definition because types may refer back to
    themselves, or to other types which have yet to be defined, but exist in the
    same module.
    """
    def run(self, state: State):
        self.apply(state)
        return state

    def apply(self, state: State) -> None:
        self._route(state.get_asl(), state)

    @Visitor.for_asls("start")
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_asls("mod")
    def mod_(fn, state: State):
        adapters.Mod(state).enter_module_and_apply(fn)

    @Visitor.for_asls("interface")
    def interface_(fn, state: State) -> None:
        node = adapters.Interface(state)
        node.get_this_type().finalize(
            components=[TypeParser().apply(state.but_with(asl=child))
                for child in node.get_child_attribute_asls()],
            component_names=node.get_child_attribute_names(),
            inherits=[])

    @Visitor.for_asls("struct")
    def struct_(fn, state: State) -> None:
        node = adapters.Struct(state)
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

    @Visitor.for_asls("variant")
    def variant_(fn, state: State) -> None:
        node = adapters.Variant(state)
        this_variant_type = node.get_this_type()
        this_variant_type.finalize(parent_type=node.get_parent_type())

    @Visitor.for_default
    def default_(fn, state: State) -> None:
        # nothing to do by default
        return


class Finalization2(Visitor):
    def run(self, state: State):
        self.apply(state)
        return state

    def apply(self, state: State) -> None:
        self._route(state.get_asl(), state)

    @Visitor.for_asls("start")
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_asls("mod")
    def mod_(fn, state: State):
        adapters.Mod(state).enter_module_and_apply(fn)

    @Visitor.for_asls("struct")
    def struct_(fn, state: State) -> None:
        node = adapters.Struct(state)
        this_struct_type = node.get_this_type()
        this_struct_type.components = [TypeParser().apply(state.but_with(asl=asl))
            for asl in node.get_child_attribute_asls()]

    @Visitor.for_default
    def default_(fn, state: State) -> None:
        # nothing to do by default
        return
