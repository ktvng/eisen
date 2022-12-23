from __future__ import annotations

from alpaca.clr import CLRList

from eisen.common.state import State
from eisen.common.nodedata import NodeData
from eisen.validation.nodetypes import Nodes

class CallUnwrapper():
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
        if Nodes.RawCall(state).calls_member_function():
            cls._convert_to_normal_call(state)
        else:
            cls._unravel(state)
