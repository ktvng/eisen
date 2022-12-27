from __future__ import annotations

from alpaca.clr import CLRList
from alpaca.concepts import Type

from eisen.common.state import State
from eisen.validation.builtin_print import BuiltinPrint
from eisen.common.nodedata import NodeData
from eisen.validation.nodetypes import Nodes

class CallUnwrapper():
    @classmethod
    def _process2(cls, state: State):
        if cls._chains_to_correct_function(state):
            state.get_asl().update(type="call")
        else:
            params_asl = state.asl[-1]
            params_asl[:] = [state.asl.first().first(), *params_asl]
            fn_asl = CLRList(
                type="ref",
                lst=[state.asl.first().second()],
                line_number=state.get_line_number(),
                data=NodeData()) 

            state.get_asl().update(type="call", lst=[fn_asl, params_asl])

    @classmethod
    def _chains_to_correct_function(cls, state: State) -> bool:
        type = cls._follow_chain(state, state.asl.first())
        if type is None:
            return False
        if type.is_function():
            return True
        return False

    @classmethod
    def _follow_chain(cls, state: State, scope_asl: CLRList) -> Type:
        if scope_asl.type == "ref":
            node = Nodes.Ref(state.but_with(asl=scope_asl))
            if node.is_print():
                return BuiltinPrint.get_type_of_function(state)
            name = node.get_name() 
            instance = state.get_context().get_instance(name)
            return instance.type

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

    @classmethod
    def process(cls, state: State):
        cls._process2(state)
