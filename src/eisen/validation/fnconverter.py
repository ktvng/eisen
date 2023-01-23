from __future__ import annotations

from alpaca.utils import Visitor
from eisen.common.state import State
from eisen.validation.nodetypes import Nodes
from eisen.validation.lookupmanager import LookupManager

class FnConverter(Visitor):
    def apply(self, state: State):
        self._route(state.asl, state)

    @Visitor.for_tokens
    def tokens_(fn, state: State):
        return

    @Visitor.for_asls("interface")
    def no_action_(fn, state: State):
        return

    @Visitor.for_asls("def", "create", "is_fn")
    def def_(fn, state: State):
        Nodes.CommonFunction(state).enter_context_and_apply(fn)

    @Visitor.for_asls("if")
    def if_(fn, state: State):
        Nodes.If(state).enter_context_and_apply(fn)

    @Visitor.for_asls("while")
    def while_(fn, state: State):
        Nodes.While(state).enter_context_and_apply(fn)

    @Visitor.for_asls("struct")
    def struct_(fn, state: State):
        node = Nodes.Struct(state)
        if node.has_create_asl():
            fn.apply(state.but_with(asl=node.get_create_asl()))

    @Visitor.for_asls("variant")
    def variant_(fn, state: State):
        fn.apply(state.but_with(asl=Nodes.Variant(state).get_is_asl()))

    @Visitor.for_asls("let", "var", "val", ":", "var?")
    def decls_(fn, state: State):
        for name in Nodes.Decl(state).get_names():
            state.get_context().add_local_ref(name)

    @Visitor.for_asls("ilet", "ivar")
    def iletivar_(fn, state: State):
        for name in Nodes.IletIvar(state).get_names():
            state.get_context().add_local_ref(name)

    @Visitor.for_asls("ref")
    def ref_(fn, state: State):
        node = Nodes.Ref(state)
        if state.get_context().get_local_ref(node.get_name()):
            return

        fns_with_this_name = LookupManager.resolve_function_references_by_name(
            name=node.get_name(),
            mod=node.get_module())

        if fns_with_this_name:
            state.get_asl().update(type="fn")
            return

        # TODO: raise compiler error for undefined symbol

    @Visitor.for_default
    def default_(fn, state: State):
        state.apply_fn_to_all_children(fn)
