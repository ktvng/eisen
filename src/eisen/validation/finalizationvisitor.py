from __future__ import annotations

from alpaca.utils import Visitor
from eisen.state.basestate import BaseState as State
import eisen.adapters as adapters
from eisen.typecheck.typeparser import TypeParser
from eisen.validation.validate import Validate


class InterfaceFinalizationVisitor(Visitor):
    """this finalizes proto types into the fully built-out type.
    we need to separate declaration and definition because types may refer back to
    themselves, or to other types which have yet to be defined, but exist in the
    same module.
    """
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

    @Visitor.for_ast_types("interface")
    def interface_(fn, state: State) -> None:
        node = adapters.Interface(state)
        node.get_this_type().finalize(
            components=[TypeParser().apply(state.but_with(ast=child))
                for child in node.get_child_attribute_asts()],
            component_names=node.get_child_attribute_names(),
            inherits=[])

    @Visitor.for_ast_types("struct")
    def struct_(fn, state: State) -> None:
        node = adapters.Struct(state)
        this_struct_type = node.get_this_type()
        this_struct_type.finalize(
            components=[TypeParser().apply(state.but_with(ast=ast))
                for ast in node.get_child_attribute_asts()],
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


class StructFinalizationVisitor(Visitor):
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
        node = adapters.Struct(state)
        this_struct_type = node.get_this_type()
        this_struct_type.components = [TypeParser().apply(state.but_with(ast=ast))
            for ast in node.get_child_attribute_asts()]

    @Visitor.for_default
    def default_(fn, state: State) -> None:
        # nothing to do by default
        return
