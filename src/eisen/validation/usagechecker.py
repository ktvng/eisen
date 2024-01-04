from __future__ import annotations

from dataclasses import dataclass

from alpaca.utils import Visitor
from alpaca.concepts import Type, Context

from eisen.common import binary_ops, boolean_return_ops
from eisen.state.usagecheckerstate import UsageCheckerState
from eisen.common.eiseninstance import Instance
from eisen.common.restriction import (LiteralRestriction, NoRestriction,
                                      ImmutableRestriction)
from eisen.common.initialization import Initializations
from eisen.common.usagestatus import UsageStatus, UsageStatusFactory

import eisen.adapters as adapters
from eisen.validation.validate import Validate

State = UsageCheckerState
class UsageChecker(Visitor):
    def run(self, state: State):
        self.apply(UsageCheckerState.create_from_basestate(state))
        return state

    def apply(self, state: State) -> list[UsageStatus]:
        result = self._route(state.get_ast(), state)
        if result is None:
            return []
        return result

    @staticmethod
    def create_new_statuses_for_instances(
            instances: list[Instance],
            initialization: Initializations = Initializations.NotInitialized) -> list[UsageStatus]:
        return [UsageStatusFactory.create(i.name, i.type.restriction, initialization) for i in instances]

    @staticmethod
    def create_status_from_instance(instance: Instance, init_state: Initializations) -> UsageStatus:
        return UsageStatusFactory.create(instance.name, instance.type.restriction, init_state)

    @staticmethod
    def create_status_from_type(tc: Type) -> list[UsageStatus]:
        return UsageStatusFactory.create_anonymous(tc.restriction, Initializations.Initialized)

    @staticmethod
    def handle_assignment(state: State, left_statuses: list[UsageStatus], right_statuses: list[UsageStatus]):
        for left, right in zip(left_statuses, right_statuses):
            Validate.assignment_restrictions_met(state, left, right)
            # must mark as initialized after we check critera, otherwise checks may fail
            # if this is where the first initialization occurs
            left.mark_as_initialized()
            if not left.is_anonymous():
                state.add_usagestatus(left)

    @staticmethod
    def validate_all_struct_members_initialized_after_constructor(state: State, create_context: Context):
        # check that all attributes are initialized
        internal_state = state.but_with(context=create_context)
        if state.get_ast().type == "create":
            for attr in state.get_instances()[0].type.get_return_type().component_names:
                Validate.attribute_is_initialized(state, attr, internal_state.get_usagestatus(
                    name=adapters.Create(state).get_name_of_created_entity()))


    @Visitor.for_ast_types("rets")
    def _rets(fn, state: State):
        if state.get_child_asts():
            rets = fn.apply(state.but_with_first_child())
            # Return types inside a constructor should be marked as initialized
            if state.is_inside_constructor():
                for ret, type_ in zip(rets, state.get_returned_type().unpack_into_parts()):
                    ret.mark_as_underconstruction(type_)

    @Visitor.for_ast_types("args", "prod_type")
    def args_(fn, state: State):
        for child in state.get_all_children():
            for inst in fn.apply(state.but_with(ast=child)):
                inst.mark_as_initialized()

    @Visitor.for_ast_types("start", "seq", "cond")
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_ast_types("mod")
    def mod_(fn, state: State):
        adapters.Mod(state).enter_module_and_apply(fn)

    @Visitor.for_ast_types("def", "is_fn")
    def defs_(fn, state: State) -> list[UsageStatus]:
        adapters.CommonFunction(state).enter_context_and_apply(fn)

    @Visitor.for_ast_types("create")
    def create_(fn, state: State) -> list[UsageStatus]:
        # must create fn_context here as it is shared by all children
        fn_context = state.create_block_context()
        for child in state.get_child_asts():
            fn.apply(state.but_with(
                ast=child,
                context=fn_context,
                inside_constructor=True))

        UsageChecker.validate_all_struct_members_initialized_after_constructor(
            state=state,
            create_context=fn_context)

    @Visitor.for_ast_types("interface", "return")
    def none_(fn, state: State) -> list[UsageStatus]:
        return []

    @Visitor.for_ast_types("struct")
    def struct_(fn, state: State) -> list[UsageStatus]:
        node = adapters.Struct(state)
        if node.has_create_ast():
            fn.apply(state.but_with(ast=node.get_create_ast()))

    @Visitor.for_ast_types("variant")
    def variant_(fn, state: State) -> list[Instance]:
        fn.apply(state.but_with(ast=adapters.Variant(state).get_is_ast()))

    @Visitor.for_ast_types("if")
    def if_(fn, state: State) -> list[UsageStatus]:
        adapters.If(state).enter_context_and_apply(fn)

    @Visitor.for_ast_types("while")
    def while_(fn, state: State) -> list[UsageStatus]:
        adapters.While(state).enter_context_and_apply(fn)

    @Visitor.for_ast_types("ref")
    def ref_(fn, state: State) -> list[UsageStatus]:
        return [state.get_usagestatus(adapters.Ref(state).get_name())]

    @Visitor.for_ast_types("fn")
    def fn_(fn, state: State) -> list[UsageStatus]:
        return UsageChecker.create_new_statuses_for_instances(
            instances=state.get_instances(),
            initialization=Initializations.Initialized)

    @Visitor.for_ast_types(*adapters.Typing.ast_types)
    def let_(fn, state: State) -> list[UsageStatus]:
        statuses = UsageChecker.create_new_statuses_for_instances(instances=state.get_instances())
        for status in statuses:
            state.add_usagestatus(status)
        return statuses

    @Visitor.for_ast_types(*adapters.InferenceAssign.ast_types)
    def ilet_(fn, state: State) -> list[UsageStatus]:
        UsageChecker.handle_assignment(state,
            left_statuses=UsageChecker.create_new_statuses_for_instances(state.get_instances()),
            right_statuses=fn.apply(state.but_with(ast=state.second_child())))

    @Visitor.for_ast_types("tuple", "params", "curried")
    def tuple_(fn, state: State) -> list[UsageStatus]:
        statuses = []
        for child in state.get_all_children():
            statuses += fn.apply(state.but_with(ast=child))
        return statuses

    @Visitor.for_ast_types("=")
    def equals_(fn, state: State) -> list[UsageStatus]:
        left_entity_statuses = LValUsageVisitor().apply(state.but_with_first_child())
        right_statuses = fn.apply(state.but_with(ast=state.second_child()))
        for status in right_statuses:
            Validate.status_is_initialized(state, status)

        for left, right in zip(left_entity_statuses, right_statuses):
            Validate.assignment_restrictions_met(state, left.branch_status, right)
            # must mark as initialized after we check critera, otherwise checks may fail
            # if this is where the first initialization occurs
            left.parent_status.mark_as_initialized(left.attribute_name)
            if not left.parent_status.is_anonymous():
                state.add_usagestatus(left.parent_status)

    @Visitor.for_ast_types(".")
    def dot_(fn, state: State) -> list[UsageStatus]:
        parent_inst = fn.apply(state.but_with_first_child())[0]
        Validate.status_is_initialized(state, parent_inst)

        # Val restrictions carry over from parents. All other restrictions defer to the
        # child.
        if parent_inst.restriction.is_immutable():
            return [parent_inst]

        return [UsageStatusFactory.create(
            name=adapters.Scope(state).get_full_name(),
            restriction=state.get_restriction(),
            initialization=Initializations.Initialized)]

    @Visitor.for_ast_types("call", "is_call")
    def call_(fn, state: State) -> list[UsageStatus]:
        node = adapters.Call(state)
        if node.is_print():
            fn.apply(state.but_with(ast=node.get_params_ast()))
            return [UsageStatus.no_restriction()]

        argument_insts = [UsageChecker.create_status_from_type(tc)
            for tc in node.get_function_argument_type().unpack_into_parts()]

        param_insts = fn.apply(state.but_with(ast=node.get_params_ast()))
        for argument_requires, given in zip(argument_insts, param_insts):
            Validate.parameter_assignment_restrictions_met(state, argument_requires, given)
            Validate.status_is_initialized(state, given)

        # handle returned restrictions
        returned_insts = [UsageChecker.create_status_from_type(tc)
            for tc in node.get_function_return_type().unpack_into_parts()]
        return returned_insts

    @Visitor.for_ast_types("curry_call")
    def curry_call_(fn, state: State) -> list[UsageStatus]:
        node = adapters.CurriedCall(state)

        argument_insts = [UsageChecker.create_status_from_type(tc)
            for tc in node.get_function_argument_type().unpack_into_parts()]

        param_insts = fn.apply(state.but_with(ast=node.get_params_ast()))
        for argument_requires, given in zip(argument_insts, param_insts):
            Validate.parameter_assignment_restrictions_met(state, argument_requires, given)
            Validate.status_is_initialized(state, given)

        return [UsageStatusFactory.create_anonymous(ImmutableRestriction(), Initializations.Initialized)]

    @Visitor.for_ast_types("cast")
    def cast_(fn, state: State) -> list[UsageStatus]:
        # restriction is carried over from the second child?
        return fn.apply(state.but_with_second_child())

    @Visitor.for_ast_types(*(binary_ops + boolean_return_ops), "!")
    def ops_(fn, state: State) -> list[UsageStatus]:
        for child in state.get_all_children():
            for status in fn.apply(state.but_with(ast=child)):
                Validate.status_is_initialized(state, status)
        return [UsageStatusFactory.create_anonymous(LiteralRestriction(), Initializations.Initialized)]

    @Visitor.for_ast_types("index", "type", "new_vec", "mut_type")
    def index_(fn, state: State) -> list[UsageStatus]:
        return [UsageStatusFactory.create_anonymous(state.get_restriction(), Initializations.Initialized)]

    @Visitor.for_tokens
    def token_(fn, state: State) -> list[UsageStatus]:
        if state.get_ast().value == "nil":
            return [UsageStatusFactory.create_anonymous(NoRestriction(), Initializations.Initialized)]
        return [UsageStatusFactory.create_anonymous(LiteralRestriction(), Initializations.Initialized)]

    @Visitor.for_default
    def default_(fn, state: State) -> list[UsageStatus]:
        print("UsageChecker Unhandled State:", state.get_ast())
        exit()

    @Visitor.for_ast_types("annotation")
    def annotation_(fn, state: State) -> list[UsageStatus]:
        # Not implemented
        return []





@dataclass
class LValUsageStatus:
    """
    For an L-value, it is necessary to include additional information beyond just the UsageStatus
    that gets passed back. In particular, it is necessary to include information about the parent
    object in cases of scope resolution (e.g. obj.attr). This is because if the object is under
    construction, certain attributes may or may not be initialized.
    """
    parent_status: UsageStatus
    branch_status: UsageStatus
    attribute_name: str = None

class LValUsageVisitor(Visitor):
    def run(self, state: State):
        self.apply(state)
        return state

    def apply(self, state: State) -> list[LValUsageStatus]:
        result = self._route(state.get_ast(), state)
        if result is None:
            return []
        return result

    @Visitor.for_ast_types("lvals")
    def lvals_(self, state: State):
        statuses = []
        for child in state.get_all_children():
            statuses += self.apply(state.but_with(ast=child))
        return statuses

    @Visitor.for_ast_types("ref")
    def ref_(self, state: State):
        parent_status = state.get_usagestatus(adapters.Ref(state).get_name())
        return [LValUsageStatus(
            parent_status=parent_status,
            branch_status=UsageStatusFactory.create_anonymous(parent_status.restriction, parent_status.initialization))]

    @Visitor.for_ast_types(".")
    def dot_(self, state: State):
        node = adapters.Scope(state)
        entitystatus = self.apply(state.but_with_first_child())[0]

        branch_restriction = state.get_restriction()
        if (entitystatus.parent_status.is_under_construction()
                and entitystatus.parent_status.get_initialization_of_attribute(node.get_attribute_name()) == Initializations.NotInitialized):
            # attribute has not yet been constructed
            if branch_restriction.is_immutable(): branch_restriction = ImmutableRestriction()
            return [LValUsageStatus(
                parent_status=entitystatus.parent_status,
                branch_status=UsageStatusFactory.create(node.get_full_name(), branch_restriction, Initializations.NotInitialized),
                attribute_name=node.get_attribute_name())]

        if entitystatus.branch_status.restriction.is_immutable():
            entitystatus.branch_status._modifies_val_state = True
            return [entitystatus]
        elif branch_restriction.is_immutable():
            return [LValUsageStatus(
                parent_status=entitystatus.parent_status,
                branch_status=UsageStatusFactory.create(node.get_full_name(), ImmutableRestriction(), Initializations.Initialized))]

        return [LValUsageStatus(
            parent_status=entitystatus.parent_status,
            branch_status=UsageStatusFactory.create(node.get_full_name(), branch_restriction, Initializations.Initialized))]
