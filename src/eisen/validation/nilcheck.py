from __future__ import annotations

from alpaca.utils import Visitor

from eisen.common import binary_ops, boolean_return_ops
from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor
from eisen.validation.validate import Validate
import eisen.adapters as adapters
from eisen.validation.nilablestatus import NilableStatus

State = State_PostInstanceVisitor

class NilCheck(Visitor):
    def run(self, state: State):
        self.apply(state)
        return state

    def apply(self, state: State) -> list[NilableStatus]:
        # print(state.asl)
        return self._route(state.asl, state)

    @classmethod
    def get_nilstate(self, state: State, name) -> bool:
        return state.get_context().get_nilstate(name)

    @classmethod
    def add_nilstate(self, state: State, name: str, nilstate: bool):
        state.get_context().add_nilstate(name, nilstate)


    @classmethod
    def anonymous_nilablestatus(cls, is_nilable: bool) -> list[NilableStatus]:
        return [NilableStatus("", is_nilable)]

    @Visitor.for_tokens
    def tokens_(fn, state: State):
        if state.asl.value == "nil":
            return NilableStatus("nil", True)
        return NilCheck.anonymous_nilablestatus(is_nilable=False)

    @Visitor.for_asls("start", "seq", "mod", "args", "rets", "params", "cond", "prod_type", "is")
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)
        return []

    @Visitor.for_asls("if")
    def if_(fn, state: State):
        adapters.If(state).enter_context_and_apply(fn)

    @Visitor.for_asls("while")
    def while_(fn, state: State):
        adapters.While(state).enter_context_and_apply(fn)

    @Visitor.for_asls("def", "create", "is_fn")
    def fns_(fn, state: State):
        adapters.CommonFunction(state).enter_context_and_apply(fn)
        return NilCheck.anonymous_nilablestatus(is_nilable=False)

    @Visitor.for_asls(*binary_ops, *boolean_return_ops)
    def ops_(fn, state: State):
        left_states = fn.apply(state.but_with_first_child())
        right_states = fn.apply(state.but_with_second_child())

        for left, right in zip(left_states, right_states):
            result = Validate.both_operands_are_not_nilable(state, left, right)
            if result.failed():
                return state.get_abort_signal()

        return NilCheck.anonymous_nilablestatus(is_nilable=False)

    # TODO: fix this
    @Visitor.for_asls("=", "<-", "fn")
    def assigns_(fn, state: State):
        return NilCheck.anonymous_nilablestatus(is_nilable=False)

    @Visitor.for_asls("call", "is_call")
    def call_(fn, state: State):
        fn.apply(state.but_with(asl=adapters.Call(state).get_params_asl()))
        if state.get_returned_type().is_tuple():
            return [NilableStatus(name="", is_nilable=type.restriction.is_nullable())
                for type in state.get_returned_type().components]
        return NilCheck.anonymous_nilablestatus(
            is_nilable=state.get_returned_type().restriction.is_nullable())

    @Visitor.for_asls("ref")
    def ref_(fn, state: State):
        node = adapters.Ref(state)
        return [NilableStatus(node.get_name(), NilCheck.get_nilstate(state, node.get_name()))]

    @Visitor.for_asls("var?")
    def nullable_var_(fn, state: State):
        for name in adapters.Decl(state).get_names():
            NilCheck.add_nilstate(state, name, True)
        return []

    @Visitor.for_asls("let", "var", "val")
    def let_(fn, state: State):
        for name in adapters.Decl(state).get_names():
            NilCheck.add_nilstate(state, name, False)
        return []

    @Visitor.for_asls("ilet", "ivar")
    def ilet_(fn, state: State):
        for name in adapters.IletIvar(state).get_names():
            NilCheck.add_nilstate(state, name, False)
        return []

    @Visitor.for_asls("cast")
    def cast_(fn, state: State):
        return NilCheck.anonymous_nilablestatus(
            is_nilable=state.but_with_second_child().get_returned_type().restriction.is_nullable())

    @Visitor.for_asls(":")
    def colon_(fn, state: State):
        for name in adapters.Decl(state).get_names():
            if adapters.Decl(state).get_is_var():
                NilCheck.add_nilstate(state, name, True)
            else:
                NilCheck.add_nilstate(state, name, False)
        return []

    @Visitor.for_asls(".")
    def dot_(fn, state: State):
        return NilCheck.anonymous_nilablestatus(state.get_returned_type().restriction.is_nullable())

    @Visitor.for_asls("struct")
    def struct_(fn, state: State):
        if adapters.Struct(state).has_create_asl():
            fn.apply(state.but_with(asl=adapters.Struct(state).get_create_asl()))
        return []

    @Visitor.for_asls("interface", "return")
    def interface_(fn, state: State):
        # nothing to do
        return []

    @Visitor.for_asls("variant")
    def variant_(fn, state: State):
        fn.apply(state.but_with(asl=adapters.Variant(state).get_is_asl()))
        return []

    @Visitor.for_asls("index")
    def index_(fn, state: State):
        return []

    @Visitor.for_default
    def default_(fn, state: State):
        print(state.get_asl())
        raise Exception(f"Nilcheck not implemented for state: {state.asl}")
