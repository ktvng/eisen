from __future__ import annotations

from alpaca.utils import Visitor
from eisen.common.eiseninstance import EisenInstance
from eisen.state.basestate import BaseState
from eisen.state.functionvisitorstate import FunctionVisitorState
from eisen.validation.typeparser import TypeParser
import eisen.adapters as adapters

State = FunctionVisitorState

class FunctionVisitor(Visitor):
    def __init__(self, debug: bool = False):
        super().__init__(debug)
        self.local_type_parser = TypeParser()
    """this creates the function instances from (create ...) and (def ) asls. the
    instances get added to the module so they can be used and called.
    """

    def run(self, state: BaseState):
        self.apply(FunctionVisitorState.create_from_basestate(state))
        return state

    def apply(self, state: State):
        return self._route(state.get_asl(), state)

    @Visitor.for_asls("start")
    def start_(fn, state: FunctionVisitorState):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_asls("mod")
    def mod_(fn, state: FunctionVisitorState):
        adapters.Mod(state).enter_module_and_apply(fn)

    @Visitor.for_default
    def default_(fn, state: FunctionVisitorState) -> None:
        return None

    @Visitor.for_asls("struct")
    def struct_(fn, state: FunctionVisitorState) -> None:
        # we need to pass down the struct name because the (create ...) asl will
        # take on the name of the struct.
        #
        # for example, a struct named MyStruct will have a constructor method
        # called via MyStruct(...), so the (create ...)  method inside the
        # (struct MyStruct ... ) asl needs context as to the struct it is inside.
        node = adapters.Struct(state)
        if node.has_create_asl():
            fn.apply(state.but_with(
                asl=node.get_create_asl(),
                struct_name=node.get_struct_name()))

    @Visitor.for_asls("variant")
    def variant_(fn, state: FunctionVisitorState) -> None:
        node = adapters.Variant(state)
        fn.apply(state.but_with(
            asl=node.get_is_asl(),
            struct_name=node.get_variant_name()))

    @Visitor.for_asls("def")
    def def_(fn, state: FunctionVisitorState):
        instance = EisenInstance(
            name=adapters.Def(state).get_function_name(),
            type=fn.local_type_parser.apply(state),
            context=state.get_enclosing_module(),
            asl=state.get_asl())
        state.get_node_data().instances = [instance]
        state.add_function_instance_to_module(instance)

    @Visitor.for_asls("create")
    def create_(fn, state: FunctionVisitorState):
        node = adapters.Create(state)
        node.normalize(struct_name=state.get_struct_name())

        # the name of the constructor is the same as the struct
        instance = EisenInstance(
            name=node.get_name(),
            type=fn.local_type_parser.apply(state),
            context=state.get_enclosing_module(),
            asl=state.get_asl(),
            is_constructor=True)
        state.get_node_data().instances = [instance]
        state.add_function_instance_to_module(instance)

    @Visitor.for_asls("is_fn")
    def is_(fn, state: FunctionVisitorState):
        node = adapters.IsFn(state)
        node.normalize(variant_name=state.get_variant_name())

        instance = EisenInstance(
            name=node.get_name(),
            type=fn.local_type_parser.apply(state),
            context=state.get_enclosing_module(),
            asl=state.get_asl())
        state.get_node_data().instances = [instance]
        state.add_function_instance_to_module(instance)
