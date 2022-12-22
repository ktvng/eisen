from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.concepts import TypeClass, TypeClassFactory
from eisen.common.params import State
from eisen.validation.nodetypes import Nodes

################################################################################
# parses (struct ...) and (interface ...) asls into a proto_struct/proto_interface
# typeclass, which represents the declaration of the typeclass without the actual
# definition.
#
# see FinalizeProtoWrangler for more details.
class DeclarationVisitor(Visitor):
    def apply(self, state: State) -> None:
        return self._route(state.asl, state)

    def adds_typeclass_to_module(f):
        def decorator(fn, state: State) -> None:
            result: TypeClass = f(fn, state)
            state.get_enclosing_module().add_typeclass(result)
        return decorator


    @Visitor.for_asls("start")
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_asls("mod")
    def mod_(fn, state: State):
        Nodes.Mod(state).enter_module_and_apply_fn_to_child_asls(fn)

    @Visitor.for_asls("struct")
    @adds_typeclass_to_module
    def struct_(fn, state: State) -> TypeClass:
        return TypeClassFactory.produce_proto_struct_type(
            name=Nodes.Struct(state).get_struct_name(),
            mod=state.get_enclosing_module())

    @Visitor.for_asls("interface")
    @adds_typeclass_to_module
    def interface_(fn, state: State) -> TypeClass:
        return TypeClassFactory.produce_proto_interface_type(
            name=Nodes.Interface(state).get_interface_name(),
            mod=state.get_enclosing_module())


    @Visitor.for_default
    def default_(fn, state: State):
        # nothing to do by default
        return
