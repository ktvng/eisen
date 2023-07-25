from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.pattern import Pattern
from alpaca.concepts import Context

from eisen.common import math_ops, compare_ops
from eisen.state.basestate import BaseState
from eisen.state.nilcheckstate import NilCheckState
from eisen.validation.validate import Validate
import eisen.adapters as adapters
from eisen.validation.nilablestatus import NilableStatus

State = NilCheckState

class NilCheck(Visitor):
    def run(self, state: BaseState):
        self.apply(NilCheckState.create_from_basestate(state))
        return state

    def apply(self, state: State) -> list[NilableStatus]:
        result = self._route(state.get_ast(), state)
        if result is None:
            return []
        return result

    @staticmethod
    def ensure_operands_not_nil(fn, state):
        left_nilstatuses = fn.apply(state.but_with_first_child())
        right_nilstatuses = fn.apply(state.but_with_second_child())
        Validate.cannot_be_nil(state, left_nilstatuses + right_nilstatuses)

    @staticmethod
    def if_statement_is_exhaustive(state: State) -> bool:
        if state.get_all_children()[-1].type == "seq":
            return True

    @staticmethod
    def update_nil_states_after_if_statement(state: State,
                                             if_contexts: list[Context],
                                             changed_nilstates: set[NilableStatus]):
        # TODO: We need to make this more robust to handle 'or' statements
        # The special case if there is a single if statement to handle a given reference being nil,
        # which would look something like this
        #
        #   var? x = somethingThatCouldBeNil
        #   if (x == nil) {
        #       # something to set x to not nil
        #   }
        #
        # Then after this block, we should be able to assert that the nilstate for x is not nil, and
        # we want to be able to use x directly.
        match = Pattern("('if ('cond ('== ('ref name) 'nil) xs...))").match(state.get_ast())
        if len(state.get_all_children()) == 1 and match.matched:
            name = match.captures.get("name").value

            # Note: in this case, there is only one context in the if statement.
            if if_contexts[0].get_nilstatus(name).could_be_nil == False:
                state.try_update_nilstatus(name, update_with=NilableStatus.not_nil())

        # Update any nilstates which may have unconditionally been set to not nil. This means that
        # we have both:
        #   1. The if statement is exhaustive (covers all possible outcomes).
        #   2. The nilstate is non nil in all contexts of the if statement (i.e. all conditional
        #      branches).
        if NilCheck.if_statement_is_exhaustive(state):
            [state.try_update_nilstatus(ns.name, update_with=NilableStatus.not_nil())
                for ns in changed_nilstates if ns.not_nil_in_all_contexts(if_contexts)]

        # Update any nilstates which may have conditionally been set to nil inside the if statement.
        [state.try_update_nilstatus(ns.name, update_with=NilableStatus.maybe_nil())
            for ns in changed_nilstates if ns.nil_in_some_context(if_contexts)]


    @Visitor.for_tokens
    def tokens_(fn, state: State):
        if state.get_ast().value == "nil":
            return [NilableStatus("nil", is_nilable=True, could_be_nil=True)]
        return [NilableStatus.never_nil()]

    @Visitor.for_ast_types("interface", "return")
    def return_(fn, state: State):
        # nothing to do
        return

    @Visitor.for_ast_types("start", "seq", "mod", "prod_type", "is", *adapters.ArgsRets.ast_types)
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_ast_types("tuple", "curried", "params")
    def tuple_(fn, state: State):
        states = []
        for child in state.get_all_children():
            states += fn.apply(state.but_with(ast=child))
        return states

    @Visitor.for_ast_types("if")
    def if_(fn, state: State):
        changed_nilstates = set()
        if_contexts: list[Context] = []
        for child in state.get_child_asts():
            context = state.create_block_context()
            if_contexts.append(context)
            fn.apply(state.but_with(
                ast=child,
                context=context,
                changed_nilstates=changed_nilstates))
        NilCheck.update_nil_states_after_if_statement(state, if_contexts, changed_nilstates)

    @Visitor.for_ast_types("cond")
    def cond_(fn, state: State):
        fn.apply(state.but_with(ast=state.first_child(), inside_cond=True, inside_and_domain=True))
        fn.apply(state.but_with(ast=state.second_child()))

    @Visitor.for_ast_types("while")
    def while_(fn, state: State):
        adapters.While(state).enter_context_and_apply(fn)

    @Visitor.for_ast_types("def", "create", "is_fn")
    def fns_(fn, state: State):
        adapters.CommonFunction(state).enter_context_and_apply(fn)

    @Visitor.for_ast_types("!=")
    def not_eq_(fn, state: State):
        match = Pattern("('!= ('ref name) 'nil)").match(state.get_ast())
        if match.matched:
            if state.is_inside_and_domain():
                state.try_update_nilstatus(match.captures.get("name").value, NilableStatus.not_nil())
        else:
            NilCheck.ensure_operands_not_nil(fn, state)
        return [NilableStatus.never_nil()]

    @Visitor.for_ast_types("==")
    def eq_(fn, state: State):
        match = Pattern("('== LEFT 'nil").match(state.get_ast())
        if not match.matched:
            NilCheck.ensure_operands_not_nil(fn, state)
        return [NilableStatus.never_nil()]

    @Visitor.for_ast_types("=")
    def assign_(fn, state: State):
        node = adapters.Assignment(state)
        nilstatuses = fn.apply(state.but_with_second_child())
        for name, status in zip(node.get_names_of_parent_objects(), nilstatuses):
            state.try_update_nilstatus(name, status)

    @Visitor.for_ast_types("and")
    def and_(fn, state: State):
        if not state.is_inside_cond():
            # ensure narrowing happens locally, as if we are inside a cond, there
            # is a new context.
            state = state.but_with(context=state.create_block_context())
        NilCheck.ensure_operands_not_nil(fn, state)
        return [NilableStatus.never_nil()]

    @Visitor.for_ast_types("or")
    def or_(fn, state: State):
        state = state.but_with(inside_and_domain=False)
        NilCheck.ensure_operands_not_nil(fn, state)
        return [NilableStatus.never_nil()]

    @Visitor.for_ast_types(*math_ops, *compare_ops)
    def ops_(fn, state: State):
        NilCheck.ensure_operands_not_nil(fn, state)
        return [NilableStatus.never_nil()]

    @Visitor.for_ast_types("!")
    def not_(fn, state: State):
        nilstatus = fn.apply(state.but_with_first_child())[0]
        Validate.cannot_be_nil(state, nilstatus)
        return [NilableStatus.never_nil()]

    @Visitor.for_ast_types("<-", "fn", "new_vec")
    def assigns_(fn, state: State):
        return [NilableStatus.never_nil()]

    @Visitor.for_ast_types("call", "is_call", "curry_call")
    def call_(fn, state: State):
        params_states = fn.apply(state.but_with(ast=adapters.Call(state).get_params_ast()))
        arg_types = adapters.Call(state).get_function_argument_type().unpack_into_parts()

        for param_state, _type in zip(params_states, arg_types):
            if not _type.restriction.is_nilable():
                Validate.cannot_be_nil(state, param_state)

        return [NilableStatus.for_type(type)
            for type in state.get_returned_type().unpack_into_parts()]

    @Visitor.for_ast_types("ref")
    def ref_(fn, state: State):
        node = adapters.Ref(state)
        return [state.get_nilstatus(node.get_name())]

    @Visitor.for_ast_types(*adapters.Typing.ast_types)
    def let_(fn, state: State):
        node = adapters.Typing(state)
        for name in node.get_names():
            state.add_nilstatus(NilableStatus(name, is_nilable=node.get_is_nilable(), could_be_nil=node.get_is_nilable()))

    @Visitor.for_ast_types(*adapters.InferenceAssign.ast_types)
    def ilet_(fn, state: State):
        statuses = fn.apply(state.but_with_second_child())
        node = adapters.InferenceAssign(state)
        for name, status in zip(node.get_names(), statuses):
            state.add_nilstatus(NilableStatus(name, is_nilable=node.get_is_nilable(), could_be_nil=node.get_is_nilable()))
            state.try_update_nilstatus(name, status)

    @Visitor.for_ast_types("cast")
    def cast_(fn, state: State):
        node = adapters.Cast(state)
        parent_nilstatus = fn.apply(state.but_with_first_child())[0]
        cast_into_nilstatus = NilableStatus.for_type(node.get_cast_into_type()).update(parent_nilstatus)
        Validate.cast_into_non_nil_valid(state, parent_nilstatus, cast_into_nilstatus)
        return [cast_into_nilstatus]

    @Visitor.for_ast_types(".")
    def dot_(fn, state: State):
        parent_nilstatus = fn.apply(state.but_with_first_child())[0]
        Validate.cannot_be_nil(state, parent_nilstatus)
        return [NilableStatus.for_type(state.get_returned_type())]

    @Visitor.for_ast_types("struct")
    def struct_(fn, state: State):
        if adapters.Struct(state).has_create_ast():
            fn.apply(state.but_with(ast=adapters.Struct(state).get_create_ast()))

    @Visitor.for_ast_types("variant")
    def variant_(fn, state: State):
        fn.apply(state.but_with(ast=adapters.Variant(state).get_is_ast()))

    @Visitor.for_ast_types("index")
    def index_(fn, state: State):
        parent_nilstatus = fn.apply(state.but_with_first_child())[0]
        Validate.cannot_be_nil(state, parent_nilstatus)
        return [NilableStatus.for_type(state.get_returned_type())]

    @Visitor.for_ast_types("annotation")
    def annotation_(fn, state: State):
        # Not implemented
        return []
