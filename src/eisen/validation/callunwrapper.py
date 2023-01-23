from __future__ import annotations
from typing import TYPE_CHECKING

from alpaca.clr import CLRList
from alpaca.concepts import Type, TypeFactory

from eisen.common.state import State
from eisen.validation.builtin_print import BuiltinPrint
from eisen.common.nodedata import NodeData
from eisen.validation.nodetypes import Nodes

if TYPE_CHECKING:
    from eisen.validation.typechecker import TypeChecker

class CallUnwrapper():
    @classmethod
    def process(cls, state: State, guessed_params_type: Type, fn: TypeChecker) -> Type:
        """decide whether or not the call needs to be unwrapped, and returns the
        true type of the parameters"""
        if cls._chains_to_correct_function(state, guessed_params_type):
            state.get_asl().update(type="call")
            return guessed_params_type
        else:
            # TODO: update type of params asl
            params_asl = state.asl[-1]
            first_param_asl = state.asl.first().first()
            params_asl[:] = [first_param_asl, *params_asl]
            fn_asl = CLRList(
                type="fn",
                lst=[state.asl.first().second()],
                line_number=state.get_line_number(),
                data=NodeData())

            state.get_asl().update(type="call", lst=[fn_asl, params_asl])

            # Need to get the type of the first parameter
            first_param_type = fn.apply(state.but_with(asl=first_param_asl))
            if len(params_asl) == 1:
                true_type = first_param_type
            else:
                true_type = TypeFactory.produce_tuple_type(
                    components=[first_param_type, *guessed_params_type.components])

            state.but_with_second_child().get_node_data().returned_type = true_type
            return true_type

    @classmethod
    def _chains_to_correct_function(cls, state: State, guessed_params_type: Type) -> bool:
        if state.asl.first().type == "ref":
            node = Nodes.Ref(state.but_with_first_child())
            if node.is_print():
                return BuiltinPrint.get_type_of_function(state)
            return node.resolve_reference_type().is_function()
        if state.asl.first().type == "fn":
            node = Nodes.Fn(state.but_with_first_child())
            instance = node.resolve_function_instance(argument_type=guessed_params_type)
            return instance.type.is_function()
        type = cls._follow_chain(state, state.asl.first())

        if type is None:
            return False
        if type.is_function():
            return True
        return False

    @classmethod
    def _follow_chain(cls, state: State, scope_asl: CLRList) -> Type:
        if scope_asl.type == "::":
            instance = Nodes.ModuleScope(state.but_with(asl=scope_asl)).get_end_instance()
            return instance.type

        if scope_asl.type == ".":
            obj_type: Type = cls._follow_chain(state, scope_asl.first())
            if obj_type is None:
                return None
            attr = scope_asl.second().value
            if obj_type.has_member_attribute_with_name(attr):
                return obj_type.get_member_attribute_by_name(attr)
            else:
                return None
