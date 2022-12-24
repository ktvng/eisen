from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.clr import CLRList
from alpaca.concepts import TypeClass

from eisen.common import binary_ops, boolean_return_ops
from eisen.common.state import State
from eisen.common.restriction import (VarRestriction, ValRestriction,
    LetRestriction, LiteralRestriction, PrimitiveRestriction, NoRestriction, EisenInstanceState,
    EisenAnonymousInstanceState, Initializations)

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

    @Visitor.for_asls("start", "seq", "cond")
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)
        return []

    @Visitor.for_asls("mod")
    def mod_(fn, state: State):
        Nodes.Mod(state).enter_module_and_apply_fn_to_child_asls(fn)
        return []

    @Visitor.for_asls("def", "create")
    def defs_(fn, state: State) -> list[EisenInstanceState]:
        Nodes.CommonFunction(state).enter_context_and_apply_fn(fn)
        return []

    @Visitor.for_asls("args", "rets", "prod_type")
    def args_(fn, state: State) -> list[EisenInstanceState]:
        for child in state.get_child_asls():
            instancestates = fn.apply(state.but_with(asl=child))
            for instancestate in instancestates:
                instancestate.mark_as_initialized()
        return []

    @Visitor.for_asls(":")
    def colon_(fn, state: State) -> list[EisenInstanceState]:
        instance = state.get_instances()[0]
        if instance.type.restriction is not None and instance.type.restriction.is_var():
            instancestate = EisenInstanceState(instance.name, VarRestriction(), Initializations.NotInitialized)
        elif instance.type.is_novel():
            instancestate = EisenInstanceState(instance.name, PrimitiveRestriction(), Initializations.NotInitialized)
        else:
            # pass everything else by reference (variable)
            instancestate = EisenInstanceState(instance.name, VarRestriction(), Initializations.NotInitialized)

        state.add_instancestate(instancestate)
        return [instancestate]

    @Visitor.for_asls("interface")
    def none_(fn, state: State) -> list[EisenInstanceState]:
        return []
 
    @Visitor.for_asls("struct")
    def struct_(fn, state: State) -> list[EisenInstanceState]:
        node = Nodes.Struct(state)
        if node.has_create_asl():
            fn.apply(state.but_with(asl=node.get_create_asl()))
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

    @Visitor.for_asls("let")
    def let_(fn, state: State) -> list[EisenInstanceState]:
        for instance in state.get_instances():
            if instance.type.is_novel():
                instancestate = EisenInstanceState(instance.name, PrimitiveRestriction(), Initializations.NotInitialized)
            else:
                instancestate = EisenInstanceState(instance.name, LetRestriction(), Initializations.NotInitialized)
            state.add_instancestate(instancestate)
        return []


    @Visitor.for_asls("ilet")
    def ilet_(fn, state: State) -> list[EisenInstanceState]:
        right_instancestates = fn.apply(state.but_with(asl=state.second_child()))
        for instance, right_instancestate in zip(state.get_instances(), right_instancestates):
            if instance.type.is_novel():
                left_instancestate = EisenInstanceState(instance.name, PrimitiveRestriction(), Initializations.NotInitialized)
            else:
                left_instancestate = EisenInstanceState(instance.name, LetRestriction(), Initializations.NotInitialized)

            state.add_instancestate(left_instancestate)
            Validate.assignment_restrictions_met(state, left_instancestate, right_instancestate)
            # must initialize after the validation
            left_instancestate.mark_as_initialized()
        return []


    @Visitor.for_asls("ivar")
    def ivar_(fn, state: State) -> list[EisenInstanceState]:
        right_instancestates = fn.apply(state.but_with(asl=state.second_child()))
        for instance, right_instancestate in zip(state.get_instances(), right_instancestates):
            left_instancestate = EisenInstanceState(instance.name, VarRestriction(), Initializations.NotInitialized)

            state.add_instancestate(left_instancestate)
            Validate.assignment_restrictions_met(state, left_instancestate, right_instancestate)
            # must initialize after the validation
            left_instancestate.mark_as_initialized()
        return []

    @Visitor.for_asls("var")
    def var_(fn, state: State) -> list[EisenInstanceState]:
        for instance in state.get_instances():
            state.add_instancestate(
                EisenInstanceState(instance.name, VarRestriction(), Initializations.NotInitialized))
        return []


    @Visitor.for_asls("tuple", "params")
    def tuple_(fn, state: State) -> list[EisenInstanceState]:
        instancestates = []
        for child in state.get_all_children():
            instancestates += fn.apply(state.but_with(asl=child))
        return instancestates
    
    @Visitor.for_asls("=")
    def equals_(fn, state: State) -> list[EisenInstanceState]:
        node = Nodes.Assignment(state)
        left_instancestates = fn.apply(state.but_with(asl=state.first_child()))
        right_instancestates = fn.apply(state.but_with(asl=state.second_child()))

        for left_instancestate, right_instancestate in zip(left_instancestates, right_instancestates):
            Validate.assignment_restrictions_met(state, left_instancestate, right_instancestate)
            # must mark as initialized after we check critera, otherwise checks may fail
            # if this is where the first initialization occurs
            left_instancestate.mark_as_initialized()
        return []

    @Visitor.for_asls(".")
    def dot_(fn, state: State) -> list[EisenInstanceState]:
        # TODO: figure this out
        return PermissionsVisitor.NoRestrictionInstanceState()
        node = Nodes.Scope(state)
        # if we are accessing a primitive attribute, then remove it's restriction.
        if state.get_returned_typeclass().is_novel():
            return Restriction.none
        return fn.apply(state.but_with(asl=node.get_asl_defining_restriction()))

    @Visitor.for_asls("call")
    def call_(fn, state: State) -> list[EisenInstanceState]:
        node = Nodes.Call(state)

        if node.is_print():
            return PermissionsVisitor.NoRestrictionInstanceState()


        argument_converted_instancestates = []
        # handle argument instancestates
        argument_typeclass = node.get_argument_type()
        restrictions = argument_typeclass.get_restrictions()
        unpacked_argument_typeclasses = [argument_typeclass] if not argument_typeclass.is_tuple() else argument_typeclass.components
        for r, tc in zip(restrictions, unpacked_argument_typeclasses):
            if r.is_let() and tc.is_novel():
                argument_converted_instancestates.append(
                    EisenAnonymousInstanceState(PrimitiveRestriction(), Initializations.Initialized))
            elif r.is_let():
                # TODO: init should be false; should this be LET?
                argument_converted_instancestates.append(
                    EisenAnonymousInstanceState(VarRestriction(), Initializations.Initialized))
            elif r.is_var():
                argument_converted_instancestates.append(
                    EisenAnonymousInstanceState(VarRestriction(), Initializations.Initialized))

        
        param_instancestates = fn.apply(state.but_with(asl=node.get_params_asl()))
        for left, right in zip(argument_converted_instancestates, param_instancestates):
            Validate.parameter_assignment_restrictions_met(state, left, right)
 

        # handle returned restrictions
        returned_typeclass = node.get_function_return_type()
        converted_instancestates = []
        for tc in returned_typeclass.unpack_into_parts():
            converted_instancestates.append(
                PermissionsVisitor.typeclass_to_instancestate(tc, Initializations.Initialized))
        return converted_instancestates

    @Visitor.for_asls("cast")
    def cast_(fn, state: State) -> list[EisenInstanceState]:
        # restriction is carried over from the first child
        return fn.apply(state.but_with(asl=state.first_child()))

    @Visitor.for_asls(*(binary_ops + boolean_return_ops), "!")
    def ops_(fn, state: State) -> list[EisenInstanceState]:
        return [EisenAnonymousInstanceState(LiteralRestriction(), Initializations.Initialized)]

    @Visitor.for_tokens
    def token_(fn, state: State) -> list[EisenInstanceState]:
        return [EisenAnonymousInstanceState(LiteralRestriction(), Initializations.Initialized)]

    @Visitor.for_default
    def default_(fn, state: State) -> list[EisenInstanceState]:
        print("UNHANDLED", state.get_asl())
        return PermissionsVisitor.NoRestrictionInstanceState()

    @classmethod
    def NoRestrictionInstanceState(cls):
        return [EisenAnonymousInstanceState(NoRestriction(), Initializations.NotInitialized)]

    @classmethod
    def typeclass_to_instancestate(cls, typeclass: TypeClass, init_state: Initializations) -> EisenInstanceState:
        if typeclass.restriction.is_let() and typeclass.is_novel():
            return EisenAnonymousInstanceState(PrimitiveRestriction(), init_state)
        elif typeclass.restriction.is_let():
            return EisenAnonymousInstanceState(LetRestriction(), init_state)
        elif typeclass.restriction.is_var():
            return EisenAnonymousInstanceState(VarRestriction(), init_state)










