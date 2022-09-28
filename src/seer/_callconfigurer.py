from __future__ import annotations
from os import link

import alpaca
from alpaca.clr import CLRList, CLRToken
from alpaca.concepts import Context, TypeFactory, Instance, Type

from seer._params import Params
from seer._common import asls_of_type, ContextTypes, SeerInstance

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
        print(params.asl)
        if params.asl.type == "basic_call":
            cls._handle_basic_call(params)
        if cls._should_unravel(params):
            cls._unravel(params)
        else:
            cls._construct_standard_call(params)

    # case is (raw_call (ref x) (fn run) (params )))))
    @classmethod
    def _should_unravel(cls, params: Params) -> bool:
        primary_name = params.asl.first().first().value
        secondary_name = params.asl.second().first().value

        instance: Instance = params.mod.get_instance_by_name(primary_name)
        if instance.type.is_struct() and instance.type.has_member_attribute_with_name(secondary_name):
            return False
        
        return True
