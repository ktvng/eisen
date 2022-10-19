from __future__ import annotations

from alpaca.clr import CLRList
from alpaca.concepts import Instance

from seer._params import Params

class CallConfigurer():
    @classmethod
    def _unravel(cls, params: Params):
        ref_asl = params.asl[0]
        fn_asl = params.asl[1]
        params_asl = params.asl[2]
        params_asl[:] = [ref_asl, *params_asl]

        params.asl.update(
            type="call",
            lst=[fn_asl, params_asl])

    @classmethod
    def _construct_standard_call(cls, params: Params):
        ref_asl = params.asl[0]
        fn_asl = params.asl[1]
        params_asl = params.asl[2] 

        scope_asl = CLRList(
            type=".",
            lst=[ref_asl, fn_asl.first()],
            line_number=params.asl.line_number)

        new_fn_asl = CLRList(
            type="fn",
            lst=[scope_asl],
            line_number=params.asl.line_number)

        params.asl.update(
            type="call",
            lst=[new_fn_asl, params_asl])

    @classmethod
    def process(cls, params: Params):
        if params.asl.type == "basic_call":
            cls._handle_basic_call(params)
        if cls._should_unravel(params):
            cls._unravel(params)
        else:
            cls._construct_standard_call(params)


    # case is (raw_call (ref x) (fn run) (params )))))
    # note that (ref x) could also be an expression
    @classmethod
    def _should_unravel(cls, params: Params) -> bool:
        typeclass = params.but_with(asl=params.asl.first()).asl_get_typeclass()
        secondary_name = params.asl.second().first().value
        if typeclass.is_struct() and typeclass.has_member_attribute_with_name(secondary_name):
            return False

        return True
