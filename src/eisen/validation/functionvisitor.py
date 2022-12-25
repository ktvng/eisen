from __future__ import annotations

from alpaca.utils import Visitor
from eisen.common.eiseninstance import EisenInstance
from eisen.common.state import State
from eisen.validation.nodetypes import Nodes
from eisen.validation.typeparser import TypeParser

class FunctionVisitor(Visitor):
    """this creates the function instances from (create ...) and (def ) asls. the 
    instances get added to the module so they can be used and called.
    """
    def apply(self, state: State):
        return self._route(state.get_asl(), state)

    @Visitor.for_asls("start")
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_asls("mod")
    def mod_(fn, state: State):
        Nodes.Mod(state).enter_module_and_apply_fn_to_child_asls(fn)

    @Visitor.for_default
    def default_(fn, state: State) -> None:
        return None

    @Visitor.for_asls("struct")
    def struct_(fn, state: State) -> None:
        # we need to pass down the struct name because the (create ...) asl will 
        # take on the name of the struct. 
        #
        # for example, a struct named MyStruct will have a constructor method 
        # called via MyStruct(...), so the (create ...)  method inside the 
        # (struct MyStruct ... ) asl needs context as to the struct it is inside.
        node = Nodes.Struct(state)
        if node.has_create_asl():
            fn.apply(state.but_with(
                asl=node.get_create_asl(),
                struct_name=node.get_struct_name()))

    @Visitor.for_asls("variety")
    def variety_(fn, state: State) -> None:
        node = Nodes.Variety(state)
        fn.apply(state.but_with(
            asl=node.get_assert_asl(),
            struct_name=node.get_struct_name()))

    @Visitor.for_asls("def")
    def def_(fn, state: State):
        instance = EisenInstance(
                name=Nodes.Def(state).get_function_name(),
                type=TypeParser().apply(state),
                context=None,
                asl=state.get_asl())
        state.get_enclosing_module().add_instance(instance)

    @Visitor.for_asls("create")
    def create_(fn, state: State):
        node = Nodes.Create(state)
        node.normalize(struct_name=state.get_struct_name())
        
        # the name of the constructor is the same as the struct
        instance = EisenInstance(
                name=node.get_name(),
                type=TypeParser().apply(state),
                context=None,
                asl=state.get_asl(),
                is_constructor=True)
        state.get_enclosing_module().add_instance(instance)
        