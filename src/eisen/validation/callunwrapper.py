from __future__ import annotations

from alpaca.clr import CLRList

from eisen.common.params import State
from eisen.common.nodedata import NodeData
from eisen.validation.nodetypes import Nodes

class CallUnwrapper():
    @classmethod
    def _unravel(cls, params: State):
        """perform the following operation to "unravel" an asl:
            (raw_call (ref obj) (fn funcName) (params ...)))
        becomes the asl
            (call (fn funcName) (params (ref obj) ...))
        """
        node = Nodes.RawCall(params)
        params_asl = node.get_params_asl()

        # modify the contents of the params asl to include the reference as the first
        # argument.
        params_asl[:] = [node.get_ref_asl(), *params_asl]

        # update the (raw_call ...) asl with the new lst contents
        params.asl.update(
            type="call",
            lst=[node.get_fn_asl(), params_asl])

    @classmethod
    def _create_new_scope_asl(cls, node: Nodes.RawCall) -> CLRList:
        """create a scope resolution asl like (. name attribute)"""
        return CLRList(
            type=".",
            lst=[node.get_ref_asl(), node.get_fn_asl().first()],
            line_number=node.line_number(),
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
    def _convert_to_normal_call(cls, params: State):
        """convert, inplace an asl of form
            (raw_call (ref name) (fn attr) (params ...)
        to an asl of form
            (call (fn (. name attr)) (params ...)))
        """
        node = Nodes.RawCall(params)
        scope_asl = cls._create_new_scope_asl(node)
        new_fn_asl = cls._create_new_fn_asl(scope_asl)
        params.asl.update(
            type="call",
            lst=[new_fn_asl, node.get_params_asl()])

    @classmethod
    def process(cls, params: State):
        if Nodes.RawCall(params).calls_member_function():
            cls._convert_to_normal_call(params)
        else:
            cls._unravel(params)
