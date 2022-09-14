from __future__ import annotations

import alpaca
from alpaca.utils import Wrangler
from alpaca.concepts import Type, Context
from alpaca.clr import CLRList, CLRToken

from seer._params import Params
from seer._common import asls_of_type, SeerInstance
from seer._transmutation import CTransmutation
from seer._typeflowwrangler import TypeFlowWrangler

# flatten the function calls out of an expression
class Flattener(Wrangler):
    def __init__(self, debug: bool = False):
        super().__init__(debug)
        self.config = alpaca.config.parser.run("./src/seer/grammar.gm")
        self.counter = 0

    def run(self, params: Params) -> CLRList:
        asl, _ = self.apply(params)
        return asl

    def apply(self, params: Params) -> tuple[CLRList, list[CLRList]]:
        return self._apply([params], [params])

    def _produce_var_name(self) -> str:
        self.counter += 1
        return f"__var{self.counter}__"

    @Wrangler.covers(lambda x: isinstance(x, CLRToken))
    def leaf_(fn, params: Params) -> tuple[CLRList, list[CLRList]]:
        return CLRToken(params.asl.type_chain, params.asl.value, params.asl.line_number), []

    @Wrangler.default
    def default_(fn, params: Params) -> tuple[CLRList, list[CLRList]]:
        core_components = []
        fn_call_components = []
        for child in params.asl:
            if isinstance(child, CLRToken):
                core_components.append(child)
                continue

            if child.type == "call":
                # special case, need to unpack call
                decls, refs = fn.apply(params.but_with(asl=child))

                # need to pack the refs into a new tuple 
                fn_call_components.extend(decls)
                core_components.append(CLRList(
                    type="tuple",
                    lst=refs,
                    line_number=params.asl.line_number,
                    guid=params.asl.guid))

            else:
                component, fn_calls = fn.apply(params.but_with(asl=child))
                core_components.append(component)
                fn_call_components += fn_calls

        return CLRList(
            type=params.asl.type,
            lst=core_components,
            line_number=params.asl.line_number,
            guid=params.asl.guid), fn_call_components

    @Wrangler.covers(asls_of_type("params"))
    def params(fn, params: Params):
        core_components = []
        fn_call_components = []
        for child in params.asl:
            if isinstance(child, CLRToken):
                core_components.append(child)
                continue

            if child.type == "call":
                # special case, need to unpack call
                decls, refs = fn.apply(params.but_with(asl=child))
                fn_call_components.extend(decls)
                core_components.extend(refs)
            else:
                component, fn_calls = fn.apply(params.but_with(asl=child))
                core_components.append(component)
                fn_call_components += fn_calls

        return CLRList(
            type=params.asl.type,
            lst=core_components,
            line_number=params.asl.line_number,
            guid=params.asl.guid), fn_call_components


    @Wrangler.covers(asls_of_type("call"))
    def call_(fn, params: Params) -> tuple[list[CLRList], list[CLRList]]:
        # apply the function to the params of the call
        new_params, prior_decls = fn.apply(params.but_with(asl=params.asl.second()))

        # we need to drop into the original CLR which defines the original function
        # in order to get the return types.
        fn_asl = params.oracle.get_instances(params.asl.first())[0]
        rets_asl = fn_asl.asl[2]

        if not rets_asl:
            return [], []

        if rets_asl.first().type == "prod_type":
            decls, refs = fn._unpack_prod_type(params.but_with(asl=rets_asl.first()))
            print(params.asl.first(), refs)
        else:
            decls, refs = fn._unpack_type(params.but_with(asl=rets_asl.first()))
            print(params.asl.first(), refs)


        decls = [alpaca.clr.CLRParser.run(fn.config, txt) for txt in decls]
        refs = [alpaca.clr.CLRParser.run(fn.config, txt) for txt in refs]


        new_call = CLRList(
            type="call",
            lst=[params.asl.first(), new_params],
            line_number=params.asl.line_number,
            guid=params.asl.guid) 

        decls.append(new_call)

        for node in decls + refs:
            TypeFlowWrangler().apply(params.but_with(asl=node))

        decls = prior_decls + decls
        return decls, refs
        
    
    @Wrangler.covers(asls_of_type("seq"))
    def seq_(fn, params: Params) -> tuple[CLRList, list[CLRList]]:
        components = []
        for child in params.asl:
            if child.type == "call":
                decls, refs = fn.apply(params.but_with(asl=child))
                components += decls
            else:
                core, fn_calls = fn.apply(params.but_with(asl=child))
                components += fn_calls + [core]
        
        return CLRList(
            type=params.asl.type,
            lst=components,
            line_number=params.asl.line_number,
            guid=params.asl.guid), []

    # type actually looks like (: n (type int))
    def _unpack_type(self, params: Params) -> tuple[list[str], list[str]]:
        params = params.but_with(asl=params.asl.second())
        type = params.oracle.get_propagated_type(params.asl)
        if type.is_struct():
            type_name = CTransmutation.get_full_name_of_struct_type(
                name=type.name,
                context=params.oracle.get_module_of_propagated_type(params.asl))
        else:
            type_name = CTransmutation.get_name_of_type(type=type)

        var_name = self._produce_var_name()
        return [f"(let (: {var_name} (type {type_name})))"], [f"(ref {var_name})"]

    def _unpack_prod_type(self, params: Params) -> tuple[list[str], list[str]]:
        all_decls, all_refs = [], []
        for child in params.asl:
            decls, refs = self._unpack_type(params.but_with(asl=child))
            all_decls.extend(decls)
            all_refs.extend(refs)

        return all_decls, all_refs

