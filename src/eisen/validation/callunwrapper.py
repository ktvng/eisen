from __future__ import annotations

from alpaca.clr import CLRList

from eisen.common.params import State
from eisen.common.nodedata import NodeData
from eisen.validation.nodetypes import Nodes

class CallUnwrapper():
    @classmethod
    # to unravel a (raw_call ...) is to perform the following action
    #   
    #   (raw_call (ref name) (fn name) (params ...)) ->
    #   (call (fn name) (params (ref name) ...)) 
    def _unravel(cls, params: State):
        node = Nodes.RawCall(params)
        ref_asl = node.get_ref_asl()
        fn_asl = node.get_fn_identifying_asl()
        params_asl = node.get_params_asl()

        # modify the contents of the params asl to include the reference as the first
        # argument.
        params_asl[:] = [ref_asl, *params_asl]

        # update the (raw_call ...) asl with the new lst contents
        params.asl.update(
            type="call",
            lst=[fn_asl, params_asl])

    @classmethod
    def _construct_standard_call(cls, params: State):
        node = Nodes.RawCall(params)
        ref_asl = node.get_ref_asl()
        fn_asl = node.get_fn_identifying_asl()
        print(fn_asl)
        params_asl = node.get_params_asl()

        scope_asl = CLRList(
            type=".",
            lst=[ref_asl, fn_asl.first()],
            line_number=params.asl.line_number,
            data=NodeData())

        new_fn_asl = CLRList(
            type="fn",
            lst=[scope_asl],
            line_number=params.asl.line_number,
            data=NodeData())

        params.asl.update(
            type="call",
            lst=[new_fn_asl, params_asl])

    @classmethod
    def process(cls, params: State):
        if cls._should_unravel(params):
            cls._unravel(params)
            return
        cls._construct_standard_call(params)


    # case is (raw_call (ref x) (fn run) (params )))))
    # note that (ref x) could also be an expression
    @classmethod
    def _should_unravel(cls, params: State) -> bool:
        typeclass = params.but_with(asl=params.asl.first()).get_returned_typeclass()
        secondary_name = params.asl.second().first().value
        if typeclass.is_struct() and typeclass.has_member_attribute_with_name(secondary_name):
            return False

        return True
