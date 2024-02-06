from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.concepts import Type

from eisen.common import binary_ops, boolean_return_ops
from eisen.bindings.bindingcheckerstate import BindingCheckerState
from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor
from eisen.common.binding import Binding, Condition, BindingCondition

from eisen.bindings.branchfuser import BranchFuser
from eisen.bindings.dotastbindingresolver import DotAstBindingResolver

import eisen.adapters as adapters
from eisen.validation.validate import Validate

State = BindingCheckerState
class BindingChecker(Visitor):
    def run(self, state: State_PostInstanceVisitor):
        self.apply(BindingCheckerState.create_from_basestate(state))
        return state

    def apply(self, state: State) -> list[BindingCondition]:
        result = self._route(state.get_ast(), state)
        if result is None: return []
        return result

    @Visitor.for_ast_types("start", "seq", "cond", "prod_type", "mod")
    def _apply_all(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_ast_types("tuple", "params", "curried")
    def _apply_and_return(fn, state: State):
        returns = []
        for child in state.get_all_children():
            returns.extend(fn.apply(state.but_with(ast=child)))
        return returns

    @Visitor.for_ast_types("struct")
    def _struct(fn, state: State):
        adapters.Struct(state).apply_fn_to_create_ast(fn)

    @Visitor.for_ast_types("def")
    def _def(fn, state: State):
        adapters.CommonFunction(state).enter_context_and_apply(fn)

    @Visitor.for_ast_types("create")
    def _create(fn, state: State):
        node = adapters.Create(state)
        constructor_state = state.but_with(inside_constructor=True, context=state.create_block_context())
        constructor_state.apply_fn_to_all_child_asts(fn)

        Validate.Bindings.all_struct_members_initialized_after_constructor(
            state=state,
            struct_type=node.get_type_of_created_entity(),
            binding_condition=constructor_state.get_binding_condition(node.get_name_of_created_entity()))

    @Visitor.for_ast_types(*adapters.ArgsRets.ast_types) # "args" "rets"
    def _typing(fn, state: State):
        match state.get_ast_type(), state.is_inside_constructor():
            case "args", _: condition = Condition.initialized
            case "rets", True: condition = Condition.under_construction
            case "rets", False: condition = Condition.not_initialized

        state.but_with(environment_condition=condition).apply_fn_to_all_children(fn)

    @Visitor.for_ast_types(":")
    def _colon(fn, state: State):
        node = adapters.Colon(state)
        state.add_binding_condition(BindingCondition.create_for_arguments_or_return_values(
            reference_name=node.get_name(),
            condition=state.get_condition_due_to_environment(),
            reference_type=state.get_returned_type()))

    @Visitor.for_ast_types("=")
    def _eq(fn, state: State):
        left_child = state.but_with_first_child()
        right_child = state.but_with_second_child()

        if state.but_with_first_child().get_returned_type().is_function():
            Validate.Bindings.of_types_is_compatible(state,
                expected=left_child.get_returned_type(),
                received=right_child.get_returned_type())

        for l, r in zip(fn.apply(left_child), fn.apply(right_child)):
            Validate.Bindings.are_compatible_for_assignment(state, l, r)
            state.add_binding_condition(l.but_initialized())

    @Visitor.for_ast_types(*binary_ops, *boolean_return_ops, "!")
    def _binop(fn, state: State):
        for child in state.get_all_children():
            Validate.Bindings.are_all_initialized(state, fn.apply(state.but_with(ast=child)))

        return [BindingCondition.create_anonymous()]

    @Visitor.for_ast_types("lvals")
    def _lvals(self, state: State):
        statuses = []
        for child in state.get_all_children():
            statuses += self.apply(state.but_with(ast=child))
        return statuses

    @Visitor.for_ast_types("ref")
    def _ref(fn, state: State):
        return [state.get_binding_condition(adapters.Ref(state).get_name())]

    @Visitor.for_ast_types("fn")
    def _fn(fn, _: State):
        return [BindingCondition.create_anonymous()]

    @Visitor.for_ast_types("ilet")
    def _ilet(fn, state: State):
        Validate.Bindings.are_all_initialized(state, fn.apply(state.but_with_second_child()))

        # Create new BindingConditions for each defined reference.
        names = adapters.InferenceAssign(state).get_names()
        bindings = state.get_returned_bindings()
        for name, binding in zip(names, bindings):
            state.add_binding_condition(
                BindingCondition.create_for_reference(name, binding, Condition.initialized))

    @Visitor.for_ast_types("let")
    def _let(fn, state: State):
        node = adapters.Decl(state)
        for name, binding in zip(node.get_names(), state.get_returned_bindings()):
            state.add_binding_condition(
                BindingCondition.create_for_reference(name, binding, Condition.not_initialized))

    @Visitor.for_ast_types("call", "curry_call")
    def _call(fn, state: State):
        node = adapters.Call(state)
        if node.is_print():
            fn.apply(state.but_with(ast=node.get_params_ast()))
            return

        if node.is_append():
            # TODO: make append work
            return

        Validate.Bindings.are_all_initialized(state, fn.apply(state.but_with(ast=node.get_params_ast())))
        Validate.Bindings.of_types_is_compatible(
            state=state,
            expected=node.get_function_argument_type(),
            received=state.but_with_second_child().get_returned_type())

        return [BindingCondition.create_anonymous(binding) for binding in state.get_returned_bindings()]

    @Visitor.for_ast_types("cast")
    def _cast(fn, state: State):
        # restriction is carried over from the first child?
        return fn.apply(state.but_with_first_child())

    @Visitor.for_ast_types(".")
    def _dot(fn, state: State):
        return [DotAstBindingResolver().apply(state)]

    @Visitor.for_ast_types("::")
    def _mod_scope(fn, _: State):
        raise Exception("We don't support global variables at the module scope yet?")

    @Visitor.for_ast_types("if")
    def _if(fn, state: State):
        branch_states = [BranchFuser.apply_fn_in_branch_and_return_branch_state(state, fn, child)
                         for child in state.get_child_asts()]
        BranchFuser.check_conditional_initialization(state, branch_states)

    @Visitor.for_ast_types("while")
    def _while(fn, state: State):
        fn.apply(state.but_with_first_child())

        # Call again to see if anything was initialized during the first run of the while
        fn.apply(state.but_with_first_child())

    @Visitor.for_ast_types("new_vec", "index")
    def _TODO(fn, state: State):
        return []

    @Visitor.for_ast_types("annotation")
    def annotation_(fn, _: State) -> Type:
        # No annotations supported
        return

    @Visitor.for_ast_types("return", "interface")
    def _noop(fn, _: State):
        return []

    @Visitor.for_tokens
    def _tokens(fn, _: State):
        return [BindingCondition.create_anonymous(Binding.data)]
