from __future__ import annotations
from typing import TYPE_CHECKING

from alpaca.clr import CLRList
from alpaca.concepts import Type, TypeFactory

from eisen.common.state import State
from eisen.validation.builtin_print import BuiltinPrint
from eisen.common.nodedata import NodeData
from eisen.validation.nodetypes import Nodes

if TYPE_CHECKING:
    from eisen.validation.flowvisitor import FlowVisitor

class CallUnwrapper():
    @classmethod
    def process(cls, state: State, guessed_params_type: Type, fn: FlowVisitor) -> Type:
        if cls._chains_to_correct_function(state, guessed_params_type):
            ref_asl = state.get_asl().first()
            if ref_asl.type != "ref":
                new_ref_asl = CLRList("ref", [ref_asl], line_number=state.get_line_number(), data=NodeData())
            else:
                new_ref_asl = ref_asl
            state.get_asl().update(type="call", lst=[new_ref_asl, state.get_asl()[-1]])
            return guessed_params_type
        else:
            # TODO: update type of params asl
            params_asl = state.asl[-1]
            first_param_asl = state.asl.first().first()
            params_asl[:] = [first_param_asl, *params_asl]
            fn_asl = CLRList(
                type="ref",
                lst=[state.asl.first().second()],
                line_number=state.get_line_number(),
                data=NodeData()) 

            state.get_asl().update(type="call", lst=[fn_asl, params_asl])

            # Need to get the type of the first parameter 
            first_param_type = fn.apply(state.but_with(asl=first_param_asl))
            if len(params_asl) == 1:
                return  first_param_type
            else:
                return TypeFactory.produce_tuple_type(
                    components=[first_param_type, *guessed_params_type.components])

    @classmethod
    def _chains_to_correct_function(cls, state: State, guessed_params_type: Type) -> bool:
        if state.asl.first().type == "ref":
            node = Nodes.Ref(state.but_with_first_child())
            if node.is_print():
                return BuiltinPrint.get_type_of_function(state)
            instance = node.lookup_function_instance(type=guessed_params_type)
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
