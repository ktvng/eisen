from __future__ import annotations

from alpaca.utils import Visitor
from eisen.common.eiseninstance import Instance
from eisen.common.traits import TraitImplementation, TraitsLogic, TraitImplDetailsForFunctionVisitor
from eisen.state.basestate import BaseState
from eisen.state.functionvisitorstate import FunctionVisitorState
import eisen.adapters as adapters

from eisen.validation.validate import Validate

State = FunctionVisitorState

class FunctionVisitor(Visitor):
    """this creates the function instances from (create ...) and (def ) asts. the
    instances get added to the module so they can be used and called.
    """

    def __init__(self, debug: bool = False):
        super().__init__(debug)

    def run(self, state: BaseState):
        new_state = FunctionVisitorState.create_from_basestate(state)
        self.apply(new_state)
        return state

    def apply(self, state: State) -> Instance | None:
        instance = self._route(state.get_ast(), state)
        if instance is not None:
            # record the returned instances in the node_data and module
            state.add_function_instance_to_module(instance)
            state.get_node_data().instances = [instance]
        return instance

    @Visitor.for_ast_types("start")
    def start_(fn, state: FunctionVisitorState):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_ast_types("mod")
    def mod_(fn, state: FunctionVisitorState):
        adapters.Mod(state).enter_module_and_apply(fn)

    @Visitor.for_default
    def default_(fn, state: FunctionVisitorState) -> None:
        return None

    @Visitor.for_ast_types("struct")
    def struct_(fn, state: FunctionVisitorState) -> None:
        # we need to pass down the struct name because the (create ...) ast will
        # take on the name of the struct.
        #
        # for example, a struct named MyStruct will have a constructor method
        # called via MyStruct(...), so the (create ...)  method inside the
        # (struct MyStruct ... ) ast needs context as to the struct it is inside.
        node = adapters.Struct(state)
        node = adapters.Struct(state.but_with(struct_name=node.get_name())).apply_fn_to_create_ast(fn)

    @Visitor.for_ast_types("trait_def")
    def trait_def_(fn, state: FunctionVisitorState) -> None:
        node = adapters.TraitDef(state)
        trait_impl_details = TraitImplDetailsForFunctionVisitor(
            trait_name=node.get_trait_name(),
            implementing_struct_name=node.get_struct_name())

        # obtain the function instances of all child function definitions inside this (trait_def ...)
        instances = [fn.apply(state.but_with(ast=child, trait_impl_details=trait_impl_details))
                     for child in node.get_asts_of_implemented_functions()]

        trait = state.get_defined_type(node.get_trait_name())
        struct = state.get_defined_type(node.get_struct_name())
        state.add_trait_implementation(
            TraitImplementation(trait=trait, struct=struct, implementations=instances))

        Validate.Traits.implementation_is_complete(state,
            trait=trait,
            implementing_struct=struct,
            implemented_fns=instances)

    @Visitor.for_ast_types("def")
    def def_(fn, state: FunctionVisitorState):
        node = adapters.Def(state)
        if state.this_is_trait_implementation():
            name = TraitsLogic.get_name_for_instance_implementing_trait_function(
                details=state.get_trait_impl_details(),
                name_of_implemented_function=node.get_function_name())
            name_inside_trait = node.get_function_name()
        else:
            name = name = node.get_function_name()
            name_inside_trait = ""

        # TODO: TYPERPARSER
        print(state.get_type_parser2().run(state))
        return Instance(
            name=name,
            type=state.get_type_parser().apply(state),
            context=state.get_enclosing_module(),
            ast=state.get_ast(),
            name_of_trait_attribute=name_inside_trait,
            no_mangle=True if state.this_is_trait_implementation() else False)

    @Visitor.for_ast_types("create")
    def create_(fn, state: FunctionVisitorState):
        node = adapters.Create(state)
        node.normalize(struct_name=state.get_struct_name())

        # the name of the constructor is the same as the struct, and constructors are unique
        # and hence should not have type mangling
        # TODO: TYPERPARSER
        print(state.get_type_parser2().run(state))
        return Instance(
            name=node.get_name(),
            type=state.get_type_parser().apply(state),
            context=state.get_enclosing_module(),
            ast=state.get_ast(),
            is_constructor=True,
            no_mangle=True)
