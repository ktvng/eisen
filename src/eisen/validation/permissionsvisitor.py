from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.clr import CLRList
from alpaca.concepts import Type

from eisen.common import binary_ops, boolean_return_ops
from eisen.common.state import State
from eisen.common.eiseninstance import EisenInstance
from eisen.common.restriction import (VarRestriction, ValRestriction,
    LetRestriction, LiteralRestriction, PrimitiveRestriction, NoRestriction,
    NullableVarRestriction)
from eisen.common.initialization import Initializations
from eisen.common.eiseninstancestate import EisenAnonymousInstanceState, EisenInstanceState

from eisen.validation.nodetypes import Nodes
from eisen.validation.validate import Validate

class PermissionsVisitor(Visitor):
    def apply(self, state: State) -> list[EisenInstanceState]:
        if self.debug and isinstance(state.get_asl(), CLRList):
            print("\n"*64)
            print(state.inspect())
            print("\n"*4)
            input()
        return self._route(state.get_asl(), state)

    @classmethod
    def NoRestrictionInstanceState(cls):
        return [EisenAnonymousInstanceState(NoRestriction(), Initializations.NotInitialized)]

    @classmethod
    def convert_instance_to_instancestate(cls, instance: EisenInstance, init_state: Initializations) -> EisenInstanceState:
        return EisenInstanceState(instance.name, instance.type.restriction, init_state)

    @classmethod
    def convert_type_to_instancestate(cls, tc: Type) -> list[EisenInstanceState]:
        return EisenAnonymousInstanceState(tc.restriction, Initializations.Initialized)

    @Visitor.for_asls("rets")
    def _rets(fn, state: State):
        if state.is_inside_constructor():
            instancestate = fn.apply(state.but_with_first_child())[0]
            instancestate.mark_as_initialized()
        else:
            state.apply_fn_to_all_children(fn)
        return []

    @Visitor.for_asls("args", "prod_type")
    def args_(fn, state: State):
        for child in state.get_all_children():
            for instancestate in fn.apply(state.but_with(asl=child)):
                instancestate.mark_as_initialized()
        return []

    @Visitor.for_asls("start", "seq", "cond")
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)
        return []

    @Visitor.for_asls("mod")
    def mod_(fn, state: State):
        Nodes.Mod(state).enter_module_and_apply_fn_to_child_asls(fn)
        return []

    @Visitor.for_asls("def", "create", "is_fn")
    def defs_(fn, state: State) -> list[EisenInstanceState]:
        Nodes.CommonFunction(state).enter_context_and_apply_fn(fn)
        return []

    @Visitor.for_asls("interface", "return")
    def none_(fn, state: State) -> list[EisenInstanceState]:
        return []

    @Visitor.for_asls("struct")
    def struct_(fn, state: State) -> list[EisenInstanceState]:
        node = Nodes.Struct(state)
        if node.has_create_asl():
            fn.apply(state.but_with(asl=node.get_create_asl()))
        return []

    @Visitor.for_asls("variant")
    def variant_(fn, state: State) -> list[EisenInstance]:
        node = Nodes.Variant(state)
        fn.apply(state.but_with(asl=node.get_is_asl()))
        return []

    @Visitor.for_asls("if")
    def if_(fn, state: State) -> list[EisenInstanceState]:
        for child in state.get_child_asls():
            fn.apply(state.but_with(
                asl=child,
                context=state.create_block_context("if")))
        return []

    @Visitor.for_asls("while")
    def while_(fn, state: State) -> list[EisenInstanceState]:
        fn.apply(state.but_with(
            asl=state.first_child(),
            context=state.create_block_context("while")))
        return []

    @Visitor.for_asls("ref")
    def ref_(fn, state: State) -> list[EisenInstanceState]:
        return [state.get_instancestate(Nodes.Ref(state).get_name())]

    @Visitor.for_asls(":", "let", "var", "var?")
    def let_(fn, state: State) -> list[EisenInstanceState]:
        instancestates = [PermissionsVisitor.convert_instance_to_instancestate(instance, Initializations.NotInitialized)
            for instance in state.get_instances()]
        for instancestate in instancestates:
            state.add_instancestate(instancestate)
        return instancestates

    @Visitor.for_asls("ilet", "ivar")
    def ilet_(fn, state: State) -> list[EisenInstanceState]:
        left_instancestates = [PermissionsVisitor.convert_instance_to_instancestate(i, Initializations.NotInitialized)
            for i in state.get_instances()]
        right_instancestates = fn.apply(state.but_with(asl=state.second_child()))
        for left, right in zip(left_instancestates, right_instancestates):
            Validate.assignment_restrictions_met(state, left, right)

            # mark as initialized after validations
            left.mark_as_initialized()
            state.add_instancestate(left)
        return []

    @Visitor.for_asls("tuple", "params")
    def tuple_(fn, state: State) -> list[EisenInstanceState]:
        instancestates = []
        for child in state.get_all_children():
            instancestates += fn.apply(state.but_with(asl=child))
        return instancestates

    @Visitor.for_asls("=")
    def equals_(fn, state: State) -> list[EisenInstanceState]:
        left_instancestates = fn.apply(state.but_with(asl=state.first_child()))
        right_instancestates = fn.apply(state.but_with(asl=state.second_child()))

        for left_instancestate, right_instancestate in zip(left_instancestates, right_instancestates):
            Validate.assignment_restrictions_met(state, left_instancestate, right_instancestate)
            # must mark as initialized after we check critera, otherwise checks may fail
            # if this is where the first initialization occurs
            left_instancestate.mark_as_initialized()
        return []

    @Visitor.for_asls("<-")
    def larrow_(fn, state: State) -> list[EisenInstanceState]:
        left_instancestates = fn.apply(state.but_with(asl=state.first_child()))
        right_instancestates = fn.apply(state.but_with(asl=state.second_child()))

        for left_instancestate, right_instancestate in zip(left_instancestates, right_instancestates):
            Validate.overwrite_restrictions_met(state, left_instancestate, right_instancestate)
            # must mark as initialized after we check critera, otherwise checks may fail
            # if this is where the first initialization occurs
            left_instancestate.mark_as_initialized()
        return []


    @Visitor.for_asls(".")
    def dot_(fn, state: State) -> list[EisenInstanceState]:
        parent_instancestate = fn.apply(state.but_with_first_child())[0]
        result = Validate.instancestate_is_initialized(state, parent_instancestate)
        if result.failed():
            return PermissionsVisitor.NoRestrictionInstanceState()

        branch_instancestate = state.get_restriction()
        if branch_instancestate.is_primitive() and not parent_instancestate.restriction.is_val():
            return [EisenAnonymousInstanceState(branch_instancestate, Initializations.Initialized)]
        return [parent_instancestate]

    @Visitor.for_asls("call", "is_call")
    def call_(fn, state: State) -> list[EisenInstanceState]:
        node = Nodes.Call(state)
        if node.is_print():
            return PermissionsVisitor.NoRestrictionInstanceState()

        argument_instancestates = [PermissionsVisitor.convert_type_to_instancestate(tc)
            for tc in node.get_function_argument_type().unpack_into_parts()]

        param_instancestates = fn.apply(state.but_with(asl=node.get_params_asl()))
        for argument_requires, given in zip(argument_instancestates, param_instancestates):
            Validate.parameter_assignment_restrictions_met(state, argument_requires, given)
            Validate.instancestate_is_initialized(state, given)

        # handle returned restrictions
        returned_instancestates = [PermissionsVisitor.convert_type_to_instancestate(tc)
            for tc in node.get_function_return_type().unpack_into_parts()]
        return returned_instancestates

    @Visitor.for_asls("cast")
    def cast_(fn, state: State) -> list[EisenInstanceState]:
        # restriction is carried over from the first child
        return fn.apply(state.but_with(asl=state.first_child()))

    @Visitor.for_asls(*(binary_ops + boolean_return_ops), "!")
    def ops_(fn, state: State) -> list[EisenInstanceState]:
        component_instancestates = []
        for child in state.get_all_children():
            component_instancestates += fn.apply(state.but_with(asl=child))

        for instancestate in component_instancestates:
            Validate.instancestate_is_initialized(state, instancestate)

        return [EisenAnonymousInstanceState(LiteralRestriction(), Initializations.Initialized)]

    @Visitor.for_tokens
    def token_(fn, state: State) -> list[EisenInstanceState]:
        if state.asl.value == "nil":
            return PermissionsVisitor.NoRestrictionInstanceState()
        return [EisenAnonymousInstanceState(LiteralRestriction(), Initializations.Initialized)]

    @Visitor.for_default
    def default_(fn, state: State) -> list[EisenInstanceState]:
        print("UNHANDLED", state.get_asl())
        return PermissionsVisitor.NoRestrictionInstanceState()
