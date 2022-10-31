from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.concepts import TypeClass
from seer.common.params import Params
from seer.validation.nodetypes import Nodes
from seer.validation.typeclassparser import TypeclassParser
from seer.validation.validate import Validate

################################################################################
# this finalizes a proto_struct/proto_interface into a struct/interface typeclass.
# we need to separate declaration and definition because types may refer back to
# themselves, or to other types which have yet to be defined, but exist in the 
# same module.
class FinalizeProtoInterfaceWrangler(Visitor):
    def apply(self, state: Params) -> None:
        return self._route(state.asl, state)

    @Visitor.for_asls("start")
    def start_(fn, state: Params):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_asls("mod")
    def mod_(fn, state: Params):
        Nodes.Mod(state).enter_module_and_apply_fn_to_child_asls(fn)

    @Visitor.for_asls("interface")
    def interface_(fn, state: Params) -> None:
        node = Nodes.Interface(state)
        this_interface_typeclass = node.get_this_typeclass()
        
        # TODO: consider whether or not to allow interfaces to inherit from other interfaces
        this_interface_typeclass.finalize(
            components=[TypeclassParser().apply(state.but_with(asl=child)) 
                for child in node.get_child_attribute_asls()],
            component_names=node.get_child_attribute_names(),
            inherits=[])

    @Visitor.for_default
    def default_(fn, state: Params) -> None:
        # nothing to do by default
        return


class FinalizeProtoStructWrangler(Visitor):
    def apply(self, state: Params) -> None:
        return self._route(state.asl, state)

    @Visitor.for_asls("start")
    def start_(fn, state: Params):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_asls("mod")
    def mod_(fn, state: Params):
        Nodes.Mod(state).enter_module_and_apply_fn_to_child_asls(fn)
 
    @Visitor.for_asls("struct")
    def struct_(fn, state: Params) -> None:
        node = Nodes.Struct(state)
        this_struct_typeclass = node.get_this_typeclass()
        this_struct_typeclass.finalize(
            components=[TypeclassParser().apply(state.but_with(asl=asl)) 
                for asl in node.get_child_attribute_asls()],
            component_names=node.get_child_attribute_names(),
            inherits=node.get_implemented_interfaces(),
            embeds=node.get_embedded_structs())

        # perform validations
        Validate.embeddings_dont_conflict(state, this_struct_typeclass)
        Validate.all_implementations_are_complete(state, this_struct_typeclass)

    @Visitor.for_default
    def default_(fn, state: Params) -> None:
        # nothing to do by default
        return
    