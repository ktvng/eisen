from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.clr import CLRList, CLRToken
from alpaca.concepts import TypeClass, TypeClassFactory
from seer.common import asls_of_type
from seer.common.params import Params
from seer.validation.nodetypes import Nodes

class VarietyWrangler(Visitor):
    def apply(self, state: Params):
        if self.debug and isinstance(state.asl, CLRList):
            print("\n"*64)
            print(state.inspect())
            print("\n"*4)
            input()
        return self._apply([state], [state])

    @Visitor.covers(asls_of_type("start", "mod"))
    def start_(fn, state: Params):
        for child in state.get_child_asls():
            fn.apply(state.but_with(
                asl=child,
                mod=state.get_node_data().module))

    @Visitor.default
    def default_(fn, state: Params) -> None:
        return None

    @Visitor.covers(asls_of_type("variety"))
    def struct_(fn, state: Params) -> None:
        node = Nodes.Variety(state)
        variety_typeclass = TypeClassFactory.produce_variety_type(
            name=node.get_name(),
            mod=state.get_module(),
            inherits=node.get_inherited_typeclass())
        state.get_module().add_typeclass(variety_typeclass)

