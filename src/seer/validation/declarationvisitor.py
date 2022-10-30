from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.concepts import TypeClass, TypeClassFactory
from seer.common import asls_of_type
from seer.common.params import Params
from seer.validation.nodetypes import Nodes

################################################################################
# parses (struct ...) and (interface ...) asls into a proto_struct/proto_interface
# typeclass, which represents the declaration of the typeclass without the actual
# definition.
#
# see FinalizeProtoWrangler for more details.
class DeclarationVisitor(Visitor):
    def apply(self, state: Params) -> None:
        return self._apply([state], [state])

    def adds_typeclass_to_module(f):
        def decorator(fn, state: Params) -> None:
            result: TypeClass = f(fn, state)
            state.get_module().add_typeclass(result)
        return decorator

    @Visitor.covers(asls_of_type("struct"))
    @adds_typeclass_to_module
    def struct_(fn, state: Params) -> TypeClass:
        return TypeClassFactory.produce_proto_struct_type(
            name=Nodes.Struct(state).get_struct_name(),
            mod=state.get_module())

    @Visitor.covers(asls_of_type("interface"))
    @adds_typeclass_to_module
    def interface_(fn, state: Params) -> TypeClass:
        return TypeClassFactory.produce_proto_interface_type(
            name=Nodes.Interface(state).get_interface_name(),
            mod=state.get_module())

    @Visitor.covers(asls_of_type("start", "mod"))
    def general_(fn, state: Params):
        for child in state.get_child_asls():
            fn.apply(state.but_with(
                asl=child,
                mod=state.get_node_data().module))

    @Visitor.default
    def default_(fn, state: Params):
        # nothing to do by default
        return
