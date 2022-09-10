from __future__ import annotations

import alpaca
from alpaca.utils import Wrangler
from alpaca.concepts import Type, Context
from alpaca.clr import CLRList, CLRToken

from seer._params import Params
from seer._common import asls_of_type, SeerInstance

class Flattener(Wrangler):
    def __init__(self, debug: bool = False):
        super().__init__(debug)
        self.counter = 0

    def apply(self, params: Params) -> tuple[CLRList, list[CLRList]]:
        return self._apply([params], [params])

    @classmethod
    def _produce_var_name(self) -> str:
        self.counter += 1
        return f"__var{self.counter}__"

    @classmethod
    def _produce_decl_for_var(self, var_name: str, type: str) -> str:
        clr = f"(let (: {var_name} (type {type})))"
        config = alpaca.config.parser.run("./src/seer/grammar.gm")
        return alpaca.clr.CLRParser.run(config, clr)

    @Wrangler.covers(lambda x: isinstance(x, CLRToken))
    def leaf_(fn, params: Params) -> tuple[CLRList, list[CLRList]]:
        return CLRToken(params.asl.type_chain, params.asl.value, params.asl.line_number), []

    @Wrangler.default
    def default_(fn, params: Params) -> tuple[CLRList, list[CLRList]]:
        core_components = []
        fn_call_components = []
        for child in params.asl:
            child_core, child_fn_calls = fn.apply(params.but_with(asl=child))
            core_components += child_core
            fn_call_components += child_fn_calls

        return CLRList(
            type=params.asl.type,
            lst=core_components,
            line_number=params.asl.line_number), fn_call_components

    @Wrangler.covers(asls_of_type("call"))
    def call_(fn, params: Params) -> tuple[CLRList, list[CLRList]]:
        return_type: Type = params.asl.returns_type
        
        pass
    
    @Wrangler.covers(asls_of_type("seq"))
    def seq_(fn, params: Params) -> tuple[CLRList, list[CLRList]]:
        components = []
        for child in params.asl:
            core, fn_calls = fn.apply(params.but_with(asl=child))
            components += fn_calls + core
        
        return CLRList(
            type=params.asl.type,
            lst=components,
            line_number=params.asl.line_number), []



