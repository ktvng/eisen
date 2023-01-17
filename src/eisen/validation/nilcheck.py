from __future__ import annotations

from alpaca.utils import Visitor

from eisen.common import binary_ops, boolean_return_ops
from eisen.common.state import State
from eisen.validation.validate import Validate
from eisen.validation.nodetypes import Nodes
from eisen.validation.nilablestatus import NilableStatus

class NilCheck(Visitor):
    def apply(self, state: State) -> NilableStatus:
        # print(state.asl)
        return self._route(state.asl, state)

    @classmethod
    def anonymous_nilablestatus(cls, is_nilable: bool) -> NilableStatus:
        return NilableStatus("", is_nilable)

    @Visitor.for_tokens
    def tokens_(fn, state: State):
        if state.asl.value == "nil":
            return NilableStatus("nil", True)
        return NilCheck.anonymous_nilablestatus(is_nilable=False)

    @Visitor.for_asls("start", "seq", "mod", "args", "rets", "params", "if", "cond", "while", "prod_type", "is")
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_asls("def", "create", "is_fn")
    def fns_(fn, state: State):
        Nodes.CommonFunction(state).enter_context_and_apply_fn(fn)
        return NilCheck.anonymous_nilablestatus(is_nilable=False)

    @Visitor.for_asls(*binary_ops, *boolean_return_ops)
    def ops_(fn, state: State):
        left = fn.apply(state.but_with_first_child())
        right = fn.apply(state.but_with_second_child())

        result = Validate.both_operands_are_not_nilable(state, left, right)
        if result.failed():
            return result.get_failure_type()

        return NilCheck.anonymous_nilablestatus(is_nilable=False)

    # TODO: fix this
    @Visitor.for_asls("=", "<-")
    def assigns_(fn, state: State):
        return NilCheck.anonymous_nilablestatus(is_nilable=False)

    @Visitor.for_asls("call", "is_call")
    def call_(fn, state: State):
        fn.apply(state.but_with(asl=Nodes.Call(state).get_params_asl()))
        return NilCheck.anonymous_nilablestatus(
            is_nilable=state.get_returned_type().restriction.is_nullable())

    @Visitor.for_asls("ref")
    def ref_(fn, state: State):
        node = Nodes.Ref(state)
        return NilableStatus(node.get_name(), state.get_nilstate(node.get_name()))

    @Visitor.for_asls("var?")
    def nullable_var_(fn, state: State):
        for name in Nodes.Decl(state).get_names():
            state.add_nilstate(name, True)

    @Visitor.for_asls("let", "var", "val")
    def let_(fn, state: State):
        for name in Nodes.Decl(state).get_names():
            state.add_nilstate(name, False)

    @Visitor.for_asls("ilet", "ivar")
    def ilet_(fn, state: State):
        for name in Nodes.IletIvar(state).get_names():
            state.add_nilstate(name, False)

    @Visitor.for_asls("cast")
    def cast_(fn, state: State):
        return NilCheck.anonymous_nilablestatus(
            is_nilable=state.but_with_second_child().get_returned_type().restriction.is_nullable())

    @Visitor.for_asls(":")
    def colon_(fn, state: State):
        for name in Nodes.Decl(state).get_names():
            if Nodes.Decl(state).get_type_asl().type == "var_type?":
                state.add_nilstate(name, True)
            else:
                state.add_nilstate(name, False)

    @Visitor.for_asls(".")
    def dot_(fn, state: State):
        return NilCheck.anonymous_nilablestatus(state.get_returned_type().restriction.is_nullable())

    @Visitor.for_asls("struct")
    def struct_(fn, state: State):
        if Nodes.Struct(state).has_create_asl():
            fn.apply(state.but_with(asl=Nodes.Struct(state).get_create_asl()))

    @Visitor.for_asls("interface")
    def interface_(fn, state: State):
        # nothing to do
        return

    @Visitor.for_asls("variant")
    def variant_(fn, state: State):
        fn.apply(state.but_with(asl=Nodes.Variant(state).get_is_asl()))
