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
    def _unravel(cls, state: State):
        """perform the following operation to "unravel" an asl:
            (raw_call (ref obj) (fn funcName) (params ...)))
        becomes the asl
            (call (fn funcName) (params (ref obj) ...))
        """
        node = Nodes.RawCall(state)
        params_asl = node.get_params_asl()

        # modify the contents of the params asl to include the reference as the first
        # argument.
        params_asl[:] = [node.get_ref_asl(), *params_asl]

        # update the (raw_call ...) asl with the new lst contents
        state.get_asl().update(
            type="call",
            lst=[node.get_fn_asl(), params_asl])

    @classmethod
    def _create_new_scope_asl(cls, node: Nodes.RawCall) -> CLRList:
        """create a scope resolution asl like (. name attribute)"""
        return CLRList(
            type=".",
            lst=[node.get_ref_asl(), node.get_fn_asl().first()],
            line_number=node.get_line_number(),
            data=NodeData())

    @classmethod
    def _create_new_fn_asl(cls, resolves_to_fn: CLRList) -> CLRList:
        """create a new (fn ...) asl for something that resolves_to_fn"""
        return CLRList(
            type="fn",
            lst=[resolves_to_fn],
            line_number=resolves_to_fn.line_number,
            date=NodeData())

    @classmethod
    def _convert_to_normal_call(cls, state: State):
        """convert, inplace an asl of form
            (raw_call (ref name) (fn attr) (params ...)
        to an asl of form
            (call (fn (. name attr)) (params ...)))
        """
        node = Nodes.RawCall(state)
        scope_asl = cls._create_new_scope_asl(node)
        new_fn_asl = cls._create_new_fn_asl(scope_asl)
        state.get_asl().update(
            type="call",
            lst=[new_fn_asl, node.get_params_asl()])

    @classmethod
    def process(cls, state: State):
        cls._process2(state)
        return
        if Nodes.RawCall(state).calls_member_function():
            cls._convert_to_normal_call(state)
        else:
            cls._unravel(state)
