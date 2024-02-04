from __future__ import annotations

from alpaca.utils import Visitor
from eisen.state.basestate import BaseState as State
import eisen.adapters as adapters
from eisen.validation.lookupmanager import LookupManager


class FnConverter(Visitor):
    def run(self, state: State):
        self.apply(state)
        return state

    def apply(self, state: State):
        self._route(state.get_ast(), state)

    @Visitor.for_tokens
    def tokens_(fn, state: State):
        return

    @Visitor.for_ast_types("interface")
    def no_action_(fn, state: State):
        return

    @Visitor.for_ast_types("def", "create", "is_fn")
    def def_(fn, state: State):
        adapters.CommonFunction(state).enter_context_and_apply(fn)

    @Visitor.for_ast_types("if")
    def if_(fn, state: State):
        adapters.If(state).enter_context_and_apply(fn)

    @Visitor.for_ast_types("while")
    def while_(fn, state: State):
        adapters.While(state).enter_context_and_apply(fn)

    @Visitor.for_ast_types("struct")
    def struct_(fn, state: State):
        adapters.Struct(state).apply_fn_to_create_ast(fn)

    @Visitor.for_ast_types("variant")
    def variant_(fn, state: State):
        fn.apply(state.but_with(ast=adapters.Variant(state).get_is_ast()))

    @Visitor.for_ast_types(*adapters.Typing.ast_types)
    def decls_(fn, state: State):
        for name in adapters.Typing(state).get_names():
            state.get_context().add_local_ref(name)

    @Visitor.for_ast_types(*adapters.InferenceAssign.ast_types)
    def iletivar_(fn, state: State):
        for name in adapters.InferenceAssign(state).get_names():
            state.get_context().add_local_ref(name)
        fn.apply(state.but_with_second_child())

    @Visitor.for_ast_types("ref")
    def ref_(fn, state: State):
        node = adapters.Ref(state)
        if state.get_context().get_local_ref(node.get_name()):
            return

        fns_with_this_name = LookupManager.resolve_function_references_by_name(
            name=node.get_name(),
            mod=node.get_module())

        if fns_with_this_name:
            state.get_ast().update(type="fn")
            return

        # TODO: raise compiler error for undefined symbol

    @Visitor.for_default
    def default_(fn, state: State):
        state.apply_fn_to_all_children(fn)
