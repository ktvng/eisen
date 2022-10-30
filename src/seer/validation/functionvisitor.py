from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.clr import CLRList
from seer.common import asls_of_type, SeerInstance
from seer.common.params import Params
from seer.validation.nodetypes import Nodes
from seer.validation.typeclassparser import TypeclassParser

################################################################################
# this creates the function instances from (create ...) and (def ) asls. the 
# instances get added to the module so they can be used and called.
class FunctionVisitor(Visitor):
    def apply(self, state: Params):
        if self.debug and isinstance(state.asl, CLRList):
            print("\n"*64)
            print(state.inspect())
            print("\n"*4)
            input()
        return self._route(state.asl, state)

    @Visitor.for_asls("start", "mod")
    def start_(fn, state: Params):
        for child in state.get_child_asls():
            fn.apply(state.but_with(
                asl=child,
                mod=state.get_node_data().module))

    @Visitor.for_default
    def default_(fn, state: Params) -> None:
        return None

    @Visitor.for_asls("struct")
    def struct_(fn, state: Params) -> None:
        node = Nodes.Struct(state)
        # we need to pass down the struct name because the (create ...) asl will 
        # take on the name of the struct. 
        #
        # for example, a struct named MyStruct will have a constructor method 
        # called via MyStruct(...), so the (create ...)  method inside the 
        # (struct MyStruct ... ) asl needs context as to the struct it is inside.
        if node.has_create_asl():
            fn.apply(state.but_with(
                asl=node.get_create_asl(),
                struct_name=node.get_struct_name()))

    @Visitor.for_asls("variety")
    def variety_(fn, state: Params) -> None:
        node = Nodes.Variety(state)
        # we need to pass down the struct name because the (create ...) asl will 
        # take on the name of the struct. 
        #
        # for example, a struct named MyStruct will have a constructor method 
        # called via MyStruct(...), so the (create ...)  method inside the 
        # (struct MyStruct ... ) asl needs context as to the struct it is inside.
        fn.apply(state.but_with(
            asl=node.get_assert_asl(),
            struct_name=node.get_struct_name()))


    @Visitor.for_asls("def")
    def def_(fn, state: Params):
        mod = state.get_module()
        state.assign_instances(mod.add_instance(
            SeerInstance(
                name=Nodes.Def(state).get_function_name(),
                type=TypeclassParser().apply(state.but_with(mod=mod)),
                context=mod,
                asl=state.asl)))


    @Visitor.for_asls("create")
    def create_(fn, state: Params):
        node = Nodes.Create(state)
        # we need to normalize the create asl before we can use the TypeclassParser
        # on it. see method documentation for why.
        node.normalize(struct_name=state.struct_name)
        mod = state.get_module()

        # the name of the constructor is the same as the struct
        state.assign_instances(mod.add_instance(
            SeerInstance(
                name=state.struct_name,
                type=TypeclassParser().apply(state.but_with(mod=mod)),
                context=mod,
                asl=state.asl,
                is_constructor=True)))
