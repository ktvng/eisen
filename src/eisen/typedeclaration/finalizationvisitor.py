from __future__ import annotations

from alpaca.utils import Visitor
from eisen.state.basestate import BaseState
from eisen.common.binding import Binding
import eisen.adapters as adapters
from eisen.typecheck.typeparser import ProtoTypeParser, TypeParser, TypeParser2
from eisen.validation.validate import Validate

State = BaseState
class IntermediateFormVisitor(Visitor):
    """this finalizes proto types into the fully built-out type.
    we need to separate declaration and definition because types may refer back to
    themselves, or to other types which have yet to be defined, but exist in the
    same module.
    """
    def run(self, state: State) -> BaseState:
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

    @Visitor.for_ast_types("trait")
    def trait_(fn, state: State):
        node = adapters.Trait(state)
        this_trait_type = node.get_this_type()
        this_trait_type.finalize(
            components=[ProtoTypeParser().apply(state.but_with(ast=child))
                for child in node.get_child_attribute_asts()],
            component_names=node.get_child_attribute_names(),
            inherits=[])
        this_trait_type.modifier = Binding.void

        Validate.Traits.correctly_declared(state, node.get_this_type())

    @Visitor.for_ast_types("struct")
    def struct_(fn, state: State) -> None:
        node = adapters.Struct(state)
        this_struct_type = node.get_this_type()
        this_struct_type.finalize(
            components=[ProtoTypeParser().apply(state.but_with(ast=ast))
                for ast in node.get_child_attribute_asts()],
            component_names=node.get_child_attribute_names(),
            inherits=node.get_implemented_interfaces(),
            embeds=node.get_embedded_structs())
        this_struct_type.modifier = Binding.void

        # perform validations
        Validate.embeddings_dont_conflict(state, this_struct_type)
        Validate.all_implementations_are_complete(state, this_struct_type)

    @Visitor.for_default
    def default_(fn, state: State) -> None:
        # nothing to do by default
        return

class FinalizationVisitor(Visitor):
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

    @Visitor.for_ast_types("trait")
    def trait_(fn, state: State):
        node = adapters.Trait(state)

        # TODO: need to fix type abstraction
        # for c in node.get_this_type().components:
        #     print("=========")
        #     print(c)
        #     for k in c.get_return_type().unpack_into_parts():
        #         print(k.components[1].get_return_type().components[1].get_return_type().modifier, k.components[1].get_return_type().modifier, k.modifier)

        # Once to convert proto_types back to the fully fledged struct
        node.get_this_type().components = [TypeParser().apply(state.but_with(ast=child))
            for child in node.get_child_attribute_asts()]

        # # Once to convert proto_types back to the fully fledged struct
        # node.get_this_type().components = [TypeParser().apply(state.but_with(ast=child))
        #     for child in node.get_child_attribute_asts()]

        # for c in node.get_this_type().components:
        #     print("=========")
        #     for k in c.get_return_type().unpack_into_parts():
        #         print(k.components[1].get_return_type().components[1].get_return_type().modifier, k.components[1].get_return_type().modifier, k.modifier)

    @Visitor.for_default
    def default_(fn, state: State) -> None:
        # nothing to do by default
        return

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
        type_parser = TypeParser2()
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
        type_parser = TypeParser2()
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
