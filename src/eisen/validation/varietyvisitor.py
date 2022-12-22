from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.clr import CLRList, CLRToken
from alpaca.concepts import TypeClass, TypeClassFactory
from eisen.common import asls_of_type
from eisen.common.params import State
from eisen.validation.nodetypes import Nodes

class VarietyWrangler(Visitor):
    def apply(self, state: State):
        if self.debug and isinstance(state.asl, CLRList):
            print("\n"*64)
            print(state.inspect())
            print("\n"*4)
            input()
        return self._apply([state], [state])

    @Visitor.for_asls("start")
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_asls("mod")
    def mod_(fn, state: State):
        Nodes.Mod(state).enter_module_and_apply_fn_to_child_asls(fn)

    @Visitor.default
    def default_(fn, state: State) -> None:
        return None

    @Visitor.covers(asls_of_type("variety"))
    def struct_(fn, state: State) -> None:
        node = Nodes.Variety(state)
        variety_typeclass = TypeClassFactory.produce_variety_type(
            name=node.get_name(),
            mod=state.get_enclosing_module(),
            inherits=node.get_inherited_typeclass())
        state.get_enclosing_module().add_typeclass(variety_typeclass)

