from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.clr import CLRList
from alpaca.concepts import Type

from eisen.common import binary_ops, boolean_return_ops
from eisen.common.state import State
from eisen.common.eiseninstance import EisenInstance
from eisen.common.restriction import (LiteralRestriction, NoRestriction, FunctionalRestriction)
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
    def get_instancestate(cls, instance: EisenInstance, init_state: Initializations) -> EisenInstanceState:
        return EisenInstanceState(instance.name, instance.type.restriction, init_state)

    @classmethod
    def get_instancestate_from_type(cls, tc: Type) -> list[EisenInstanceState]:
        return EisenAnonymousInstanceState(tc.restriction, Initializations.Initialized)

    @Visitor.for_asls("rets")
    def _rets(fn, state: State):
        if state.is_inside_constructor():
            inst = fn.apply(state.but_with_first_child())[0]
            inst.mark_as_initialized()
        else:
            state.apply_fn_to_all_children(fn)
        return []

    @Visitor.for_asls("args", "prod_type")
    def args_(fn, state: State):
        for child in state.get_all_children():
            for inst in fn.apply(state.but_with(asl=child)):
                inst.mark_as_initialized()
        return []

    @Visitor.for_asls("start", "seq", "cond")
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)
        return []

    @Visitor.for_asls("mod")
    def mod_(fn, state: State):
        Nodes.Mod(state).enter_module_and_apply(fn)
        return []

    @Visitor.for_asls("def", "create", "is_fn")
    def defs_(fn, state: State) -> list[EisenInstanceState]:
        Nodes.CommonFunction(state).enter_context_and_apply(fn)
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
        Nodes.If(state).enter_context_and_apply(fn)
        return []

    @Visitor.for_asls("while")
    def while_(fn, state: State) -> list[EisenInstanceState]:
        Nodes.While(state).enter_context_and_apply(fn)
        return []

    def fn_(fn, state: State) -> list[EisenInstanceState]:
        pass

    @Visitor.for_asls("ref")
    def ref_(fn, state: State) -> list[EisenInstanceState]:
        return [state.get_instancestate(Nodes.Ref(state).get_name())]

    @Visitor.for_asls("fn")
    def fn_(fn, state: State) -> list[EisenInstanceState]:
        return [EisenAnonymousInstanceState(FunctionalRestriction(), Initializations.Initialized)]

    @Visitor.for_asls(":", "let", "var", "var?")
    def let_(fn, state: State) -> list[EisenInstanceState]:
        insts = [PermissionsVisitor.get_instancestate(instance, Initializations.NotInitialized)
            for instance in state.get_instances()]
        for inst in insts:
            state.add_instancestate(inst)
        return insts

    @Visitor.for_asls("ilet", "ivar")
    def ilet_(fn, state: State) -> list[EisenInstanceState]:
        left_insts = [PermissionsVisitor.get_instancestate(i, Initializations.NotInitialized)
            for i in state.get_instances()]
        right_insts = fn.apply(state.but_with(asl=state.second_child()))
        for left, right in zip(left_insts, right_insts):
            Validate.assignment_restrictions_met(state, left, right)

            # mark as initialized after validations
            left.mark_as_initialized()
            state.add_instancestate(left)
        return []

    @Visitor.for_asls("tuple", "params", "lvals")
    def tuple_(fn, state: State) -> list[EisenInstanceState]:
        insts = []
        for child in state.get_all_children():
            insts += fn.apply(state.but_with(asl=child))
        return insts

    @Visitor.for_asls("=")
    def equals_(fn, state: State) -> list[EisenInstanceState]:
        left_insts = fn.apply(state.but_with(asl=state.first_child()))
        right_insts = fn.apply(state.but_with(asl=state.second_child()))

        for left_inst, right_inst in zip(left_insts, right_insts):
            Validate.assignment_restrictions_met(state, left_inst, right_inst)
            # must mark as initialized after we check critera, otherwise checks may fail
            # if this is where the first initialization occurs
            left_inst.mark_as_initialized()
        return []

    @Visitor.for_asls("<-")
    def larrow_(fn, state: State) -> list[EisenInstanceState]:
        left_insts = fn.apply(state.but_with(asl=state.first_child()))
        right_insts = fn.apply(state.but_with(asl=state.second_child()))

        for left_inst, right_inst in zip(left_insts, right_insts):
            Validate.overwrite_restrictions_met(state, left_inst, right_inst)
            # must mark as initialized after we check critera, otherwise checks may fail
            # if this is where the first initialization occurs
            left_inst.mark_as_initialized()
        return []

    @Visitor.for_asls(".")
    def dot_(fn, state: State) -> list[EisenInstanceState]:
        parent_inst = fn.apply(state.but_with_first_child())[0]
        if Validate.instancestate_is_initialized(state, parent_inst).failed():
            return PermissionsVisitor.NoRestrictionInstanceState()

        branch_restricton = state.get_restriction()
        if not parent_inst.restriction.is_val():
            return [EisenAnonymousInstanceState(branch_restricton, Initializations.Initialized)]
        return [parent_inst]

    @Visitor.for_asls("call", "is_call")
    def call_(fn, state: State) -> list[EisenInstanceState]:
        node = Nodes.Call(state)
        if node.is_print():
            return PermissionsVisitor.NoRestrictionInstanceState()

        argument_insts = [PermissionsVisitor.get_instancestate_from_type(tc)
            for tc in node.get_function_argument_type().unpack_into_parts()]

        param_insts = fn.apply(state.but_with(asl=node.get_params_asl()))
        for argument_requires, given in zip(argument_insts, param_insts):
            Validate.parameter_assignment_restrictions_met(state, argument_requires, given)
            Validate.instancestate_is_initialized(state, given)

        # handle returned restrictions
        returned_insts = [PermissionsVisitor.get_instancestate_from_type(tc)
            for tc in node.get_function_return_type().unpack_into_parts()]
        return returned_insts

    @Visitor.for_asls("cast")
    def cast_(fn, state: State) -> list[EisenInstanceState]:
        # restriction is carried over from the first child
        return fn.apply(state.but_with(asl=state.first_child()))

    @Visitor.for_asls(*(binary_ops + boolean_return_ops), "!")
    def ops_(fn, state: State) -> list[EisenInstanceState]:
        component_insts = []
        for child in state.get_all_children():
            for inst in fn.apply(state.but_with(asl=child)):
                Validate.instancestate_is_initialized(state, inst)
        return [EisenAnonymousInstanceState(LiteralRestriction(), Initializations.Initialized)]

    @Visitor.for_tokens
    def token_(fn, state: State) -> list[EisenInstanceState]:
        if state.asl.value == "nil":
            return PermissionsVisitor.NoRestrictionInstanceState()
        return [EisenAnonymousInstanceState(LiteralRestriction(), Initializations.Initialized)]

    @Visitor.for_default
    def default_(fn, state: State) -> list[EisenInstanceState]:
        print("PermissionsVisitor Unhandled State:", state.get_asl())
        return PermissionsVisitor.NoRestrictionInstanceState()
