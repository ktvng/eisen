from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.concepts import Type

from eisen.common import binary_ops, boolean_return_ops
from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor
from eisen.state.usagecheckerstate import RestrictionVisitorState
from eisen.common.eiseninstance import EisenInstance
from eisen.common.restriction import (LiteralRestriction, NoRestriction, FunctionalRestriction,
                                      LetConstruction, PrimitiveRestriction, VarRestriction)
from eisen.common.initialization import Initializations
from eisen.common.usagestatus import UsageStatus

import eisen.adapters as adapters
from eisen.validation.validate import Validate

State = RestrictionVisitorState
class UsageChecker(Visitor):
    def run(self, state: State):
        self.apply(RestrictionVisitorState.create_from_basestate(state))
        return state

    def apply(self, state: State) -> list[UsageStatus]:
        result = self._route(state.get_asl(), state)
        if result is None:
            return []
        return result

    @classmethod
    def NoRestrictionInstanceState(cls):
        return [UsageStatus.anonymous(NoRestriction(), Initializations.NotInitialized)]

    @classmethod
    def create_instancestate(cls, instance: EisenInstance, init_state: Initializations) -> UsageStatus:
        return UsageStatus(instance.name, instance.type.restriction, init_state)

    @classmethod
    def create_instancestate_from_type(cls, tc: Type) -> list[UsageStatus]:
        return UsageStatus.anonymous(tc.restriction, Initializations.Initialized)

    @classmethod
    def add_instancestate(cls, state: State_PostInstanceVisitor, inst: UsageStatus):
        state.get_context().add_instancestate(inst)

    @classmethod
    def get_instancestate(cls, state: State_PostInstanceVisitor, name: str) -> UsageStatus:
        """canonical way to access a InstanceState by name"""
        return state.get_context().get_instancestate(name)

    @Visitor.for_asls("rets")
    def _rets(fn, state: State):
        if state.get_child_asls():
            rets = fn.apply(state.but_with_first_child())
            # Return types inside a constructor should be marked as initialized
            if state.is_inside_constructor():
                [ret.mark_as_underconstruction() for ret in rets]

    @Visitor.for_asls("args", "prod_type")
    def args_(fn, state: State):
        for child in state.get_all_children():
            for inst in fn.apply(state.but_with(asl=child)):
                inst.mark_as_initialized()

    @Visitor.for_asls("start", "seq", "cond")
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_asls("mod")
    def mod_(fn, state: State):
        adapters.Mod(state).enter_module_and_apply(fn)

    @Visitor.for_asls("def", "is_fn")
    def defs_(fn, state: State) -> list[UsageStatus]:
        adapters.CommonFunction(state).enter_context_and_apply(fn)

    @Visitor.for_asls("create")
    def create_(fn, state: State) -> list[UsageStatus]:
        # must create fn_context here as it is shared by all children
        fn_context = state.create_block_context()
        for child in state.get_child_asls():
            fn.apply(state.but_with(
                asl=child,
                context=fn_context,
                inside_constructor=True))

        # check that all attributes are initialized
        internal_state = state.but_with(context=fn_context)
        if state.get_asl().type == "create":
            for attr in state.get_instances()[0].type.get_return_type().component_names:
                Validate.attribute_is_initialized(state, attr, UsageChecker.get_instancestate(internal_state, "self"))


    @Visitor.for_asls("interface", "return")
    def none_(fn, state: State) -> list[UsageStatus]:
        return []

    @Visitor.for_asls("struct")
    def struct_(fn, state: State) -> list[UsageStatus]:
        node = adapters.Struct(state)
        if node.has_create_asl():
            fn.apply(state.but_with(asl=node.get_create_asl()))

    @Visitor.for_asls("variant")
    def variant_(fn, state: State) -> list[EisenInstance]:
        fn.apply(state.but_with(asl=adapters.Variant(state).get_is_asl()))

    @Visitor.for_asls("if")
    def if_(fn, state: State) -> list[UsageStatus]:
        adapters.If(state).enter_context_and_apply(fn)

    @Visitor.for_asls("while")
    def while_(fn, state: State) -> list[UsageStatus]:
        adapters.While(state).enter_context_and_apply(fn)

    @Visitor.for_asls("ref")
    def ref_(fn, state: State) -> list[UsageStatus]:
        return [UsageChecker.get_instancestate(state, adapters.Ref(state).get_name())]

    @Visitor.for_asls("fn")
    def fn_(fn, state: State) -> list[UsageStatus]:
        return [UsageChecker.create_instancestate(state.get_instances()[0], Initializations.Initialized)]

    @Visitor.for_asls(":", "let", "var", "var?", "val")
    def let_(fn, state: State) -> list[UsageStatus]:
        insts = [UsageChecker.create_instancestate(instance, Initializations.NotInitialized)
            for instance in state.get_instances()]
        for inst in insts:
            UsageChecker.add_instancestate(state, inst)
        return insts

    @Visitor.for_asls("ilet", "ivar", "ivar?")
    def ilet_(fn, state: State) -> list[UsageStatus]:
        left_insts = [UsageChecker.create_instancestate(i, Initializations.NotInitialized)
            for i in state.get_instances()]
        right_insts = fn.apply(state.but_with(asl=state.second_child()))
        for left, right in zip(left_insts, right_insts):
            # print(state.asl, left, right)
            Validate.assignment_restrictions_met(state, left, right)

            # mark as initialized after validations
            left.mark_as_initialized()
            UsageChecker.add_instancestate(state, left)
        return []

    @Visitor.for_asls("tuple", "params", "lvals")
    def tuple_(fn, state: State) -> list[UsageStatus]:
        insts = []
        for child in state.get_all_children():
            insts.extend(fn.apply(state.but_with(asl=child)))
        return insts

    @Visitor.for_asls("=")
    def equals_(fn, state: State) -> list[UsageStatus]:
        # need to apply right first as left might set it to be initialized
        right_insts = fn.apply(state.but_with(asl=state.second_child()))
        left_insts = fn.apply(state.but_with(asl=state.first_child(), left_of_assign=True))
        for status in right_insts:
            Validate.instancestate_is_initialized(state, status)

        for left_inst, right_inst in zip(left_insts, right_insts):
            Validate.assignment_restrictions_met(state, left_inst, right_inst)
            # must mark as initialized after we check critera, otherwise checks may fail
            # if this is where the first initialization occurs
            left_inst.mark_as_initialized()
        return []

    @Visitor.for_asls("<-")
    def larrow_(fn, state: State) -> list[UsageStatus]:
        left_insts = fn.apply(state.but_with(asl=state.first_child()))
        right_insts = fn.apply(state.but_with(asl=state.second_child()))

        for left_inst, right_inst in zip(left_insts, right_insts):
            Validate.overwrite_restrictions_met(state, left_inst, right_inst)
            # must mark as initialized after we check critera, otherwise checks may fail
            # if this is where the first initialization occurs
            left_inst.mark_as_initialized()
        return []

    @Visitor.for_asls(".")
    def dot_(fn, state: State) -> list[UsageStatus]:
        node = adapters.Scope(state)
        parent_inst = fn.apply(state.but_with_first_child())[0]

        branch_restriction = state.get_restriction()
        if parent_inst.initialization == Initializations.UnderConstruction:
            if parent_inst.get_initialization_of_attribute(node.get_attribute_name()) == Initializations.NotInitialized:
                # this is the case that we are constructing the non initialized attribute right now
                if state.is_left_of_assignment_operator():
                    parent_inst.mark_attribute_as_initialized(node.get_attribute_name())
                    if branch_restriction.is_val(): branch_restriction = VarRestriction()
                    return [UsageStatus.anonymous(branch_restriction, Initializations.NotInitialized)]
                else:
                    attribute_status = UsageStatus(
                        name=node.get_object_name() + "." + node.get_attribute_name(),
                        restriction=branch_restriction,
                        initialization=parent_inst.get_initialization_of_attribute(node.get_attribute_name()))
                    return [attribute_status]
            return [UsageStatus.anonymous(branch_restriction, Initializations.Initialized)]

        if Validate.instancestate_is_initialized(state, parent_inst).failed():
            return [UsageStatus.no_restriction()]

        if parent_inst.restriction.is_val():
            return [parent_inst]
        return [UsageStatus.anonymous(branch_restriction, Initializations.Initialized)]

    @Visitor.for_asls("call", "is_call")
    def call_(fn, state: State) -> list[UsageStatus]:
        node = adapters.Call(state)
        if node.is_print():
            return [UsageStatus.no_restriction()]

        argument_insts = [UsageChecker.create_instancestate_from_type(tc)
            for tc in node.get_function_argument_type().unpack_into_parts()]

        param_insts = fn.apply(state.but_with(asl=node.get_params_asl()))
        for argument_requires, given in zip(argument_insts, param_insts):
            Validate.parameter_assignment_restrictions_met(state, argument_requires, given)
            Validate.instancestate_is_initialized(state, given)

        # handle returned restrictions
        returned_insts = [UsageChecker.create_instancestate_from_type(tc)
            for tc in node.get_function_return_type().unpack_into_parts()]
        return returned_insts

    @Visitor.for_asls("curry_call")
    def curry_call_(fn, state: State) -> list[UsageStatus]:
        node = adapters.CurriedCall(state)
        # TODO: check arguments

        return [UsageStatus.anonymous(FunctionalRestriction(), Initializations.Initialized)]

    @Visitor.for_asls("cast")
    def cast_(fn, state: State) -> list[UsageStatus]:
        # restriction is carried over from the second child?
        return fn.apply(state.but_with_second_child())

    @Visitor.for_asls(*(binary_ops + boolean_return_ops), "!")
    def ops_(fn, state: State) -> list[UsageStatus]:
        for child in state.get_all_children():
            for inst in fn.apply(state.but_with(asl=child)):
                Validate.instancestate_is_initialized(state, inst)
        return [UsageStatus.anonymous(LiteralRestriction(), Initializations.Initialized)]

    @Visitor.for_asls("new_vec")
    def new_vec_(fn, state: State) -> list[UsageStatus]:
        return [UsageStatus.anonymous(LetConstruction(), Initializations.Initialized)]

    @Visitor.for_asls("index", "type")
    def index_(fn, state: State) -> list[UsageStatus]:
        return [UsageStatus.anonymous(state.get_restriction(), Initializations.Initialized)]

    @Visitor.for_tokens
    def token_(fn, state: State) -> list[UsageStatus]:
        if state.asl.value == "nil":
            return [UsageStatus.anonymous(NoRestriction(), Initializations.Initialized)]
        return [UsageStatus.anonymous(LiteralRestriction(), Initializations.Initialized)]

    @Visitor.for_default
    def default_(fn, state: State) -> list[UsageStatus]:
        print("UsageChecker Unhandled State:", state.get_asl())
        return UsageChecker.NoRestrictionInstanceState()
