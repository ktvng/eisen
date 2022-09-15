from __future__ import annotations

import alpaca
from alpaca.clr import CLRList, CLRToken
from alpaca.utils import Wrangler
from alpaca.concepts import Type, Context, Instance
from alpaca.validator import AbstractParams

from seer._common import asls_of_type, Utils
from seer._oracle import Oracle
from seer._params import Params as Params0

class SharedCounter():
    def __init__(self, n: int):
        self.value = n

    def __add__(self, other):
        return self.value + other

    def __iadd__(self, other):
        self.value += other
        return self

    def __str__(self):
        return str(self.value)

    def set(self, val: int):
        self.n = val

class Params(AbstractParams):
    def __init__(self, 
            asl: CLRList, 
            mod: Context,
            global_mod: Context,
            as_ptr: bool,
            counter: SharedCounter,
            oracle: Oracle,
            ):

        self.asl = asl
        self.mod = mod
        self.global_mod = global_mod
        self.as_ptr = as_ptr
        self.counter = counter
        self.oracle = oracle

    def but_with(self,
            asl: CLRList = None,
            mod: Context = None,
            global_mod: Context = None,
            as_ptr: bool = None,
            counter: SharedCounter = None,
            oracle: Oracle = None,
            ):

        return self._but_with(asl=asl, mod=mod, global_mod=global_mod, as_ptr=as_ptr, counter=counter,
            oracle=oracle)

    def inspect(self) -> str:
        if isinstance(self.asl, CLRList):
            instances = self.oracle.get_instances(self.asl)
            instance_strs = ("N/A" if instances is None 
                else ", ".join([str(i) for i in instances]))

            children_strs = []
            for child in self.asl:
                if isinstance(child, CLRList):
                    children_strs.append(f"({child.type} )")
                else:
                    children_strs.append(str(child))
            asl_info_str = f"({self.asl.type} {' '.join(children_strs)})"
            if len(asl_info_str) > 64:
                asl_info_str = asl_info_str[:64] + "..."

            return f"""
INSPECT ==================================================
----------------------------------------------------------
ASL: {asl_info_str}
{self.asl}

----------------------------------------------------------
Module: {self.mod.name} {self.mod.type}
{self.mod}

Type: {self.oracle.get_propagated_type(self.asl)}
Instances: {instance_strs}
"""
        else:
            return f"""
INSPECT ==================================================
Token: {self.asl}
"""

class CTransmutation(Wrangler):
    global_prefix = ""
    def run(self, asl: CLRList, params: Params0) -> str:
        txt = alpaca.utils.formatter.format_clr(self.apply(
            Params(asl, params.mod, params.mod, False, SharedCounter(0), params.oracle)))
        return txt

    def apply(self, params: Params) -> str:
        if self.debug and isinstance(params.asl, CLRList):
            print("\n"*64)
            print(params.inspect())
            print("\n"*4)
            input()
        return self._apply([params], [params])

    # TESTING
    @Wrangler.default
    def default_(fn, params: Params) -> str:
        return f"#{params.asl.type}"

    @classmethod
    def _main_method(cls) -> str:
        return "(def (type void) main (args ) (seq (call (fn global_main) (params ))))"

    def transmute(fn, asls: list[CLRList], params: Params) -> str:
        return " ".join([fn.apply(params.but_with(asl=asl)) for asl in asls])

    # TODO: need to make this struct name by modules
    @Wrangler.covers(lambda params: isinstance(params.asl, CLRToken))
    def token_(fn, params: Params) -> str:
        return params.asl.value

    @Wrangler.covers(asls_of_type("start"))
    def partial_1(fn, params: Params) -> str:
        return f"(start {fn.transmute(params.asl.items(), params)} {fn._main_method()})"

    @Wrangler.covers(asls_of_type("mod"))
    def partial_2(fn, params: Params) -> str:
        return f"{fn.transmute(params.asl.items()[1:], params)}"

    @Wrangler.covers(asls_of_type("struct"))
    def partial_3(fn, params: Params) -> str:
        full_name = Utils.get_full_name_of_struct(
            name=params.asl.first().value, 
            context=params.oracle.get_module(params.asl))
        attributes = [child for child in params.asl[1:] if child.type == ":"]
        attribute_strs = " ".join([fn.apply(params.but_with(asl=attr)) for attr in attributes])
        
        methods = [child for child in params.asl[1:] if child not in attributes]
        method_strs = " ".join([fn.apply(params.but_with(asl=meth)) for meth in methods])

        code = f"(struct {full_name} {attribute_strs}) {method_strs}"
        return code

    @Wrangler.covers(asls_of_type(
        "args", "seq", "+", "-", "*", "/", "<", ">", "<=", ">=", "==", "!=",
        "+=", "-=", "*=", "/=",
        "params", "if", "while", "cond", "return", "call"))
    def partial_4(fn, params: Params) -> str:
        return f"({params.asl.type} {fn.transmute(params.asl.items(), params)})"

    @Wrangler.covers(asls_of_type(":"))
    def partial_5(fn, params: Params) -> str:
        # hotfix, formalize tuples
        if (isinstance(params.asl.first(), CLRList) and params.asl.first().type == "tags"
            and params.asl.second().type == "type"):
            names = [token.value for token in params.asl.first()]
        else:
            names = [fn.apply(params.but_with(asl=params.asl.first()))]

        type = fn.apply(params.but_with(asl=params.asl.second()))
        strs = []
        for name in names:
            if params.oracle.get_propagated_type(asl=params.asl.second()).is_struct():
                strs.append(f"(struct_decl {type} {name})")
            else:
                strs.append(f"(decl {type} {name})")
        return " ".join(strs)

    # TODO make real type
    @Wrangler.covers(asls_of_type("type"))
    def partial_6(fn, params: Params) -> str:
        type: Type = params.oracle.get_propagated_type(params.asl)
        mod: Context = params.oracle.get_module_of_propagated_type(params.asl)
        if params.as_ptr:
            return f"(type (ptr {Utils.get_name_of_type(type, mod)}))"
        return f"(type {Utils.get_name_of_type(type, mod)})"

    @Wrangler.covers(asls_of_type("prod_type"))
    def partial_7(fn, params: Params) -> str:
        return fn.transmute(params.asl.items(), params)

    @Wrangler.covers(asls_of_type("def"))
    def partial_8(fn, params: Params) -> str:
        instances = params.oracle.get_instances(params.asl)
        name = Utils.get_full_name_of_function(instances[0])
        args = fn.apply(params.but_with(asl=params.asl.second()))
        rets = fn.apply(params.but_with(asl=params.asl.third()))
        seq = fn.apply(params.but_with(asl=params.asl[-1]))
        signature = args[:-1] + rets + ")"
        return f"(def (type void) {name} {signature} {seq})"

    @Wrangler.covers(asls_of_type("let"))
    def partial_9(fn, params: Params) -> str:
        return fn.apply(params.but_with(asl=params.asl.first()))

    @Wrangler.covers(asls_of_type("ilet"))
    def partial_(fn, params: Params) -> str:
        pass 

    @Wrangler.covers(asls_of_type("::"))
    def partial_11(fn, params: Params) -> str:
        return fn.apply(params.but_with(asl=params.asl.second()))

    @Wrangler.covers(asls_of_type("fn"))
    def partial_12(fn, params: Params) -> str:
        if (params.asl.first().value == "print"):
            return f"(fn print)"
        instances = params.oracle.get_instances(params.asl)
        return f"({params.asl.type} {Utils.get_full_name_of_function(instances[0])})"

    @Wrangler.covers(asls_of_type("rets"))
    def partial_13(fn, params: Params) -> str:
        if not params.asl:
            return ""
        return fn.apply(params.but_with(asl=params.asl.first(), as_ptr=True))

    @Wrangler.covers(asls_of_type("ref"))
    def partial_14(fn, params: Params) -> str:
        instances = params.oracle.get_instances(params.asl)
        if instances[0].is_ptr:
            return f"({params.asl.type} (deref {fn.apply(params.but_with(asl=params.asl.first()))}))"
        return f"({params.asl.type} {fn.apply(params.but_with(asl=params.asl.first()))})"

    @Wrangler.covers(asls_of_type("="))
    def partial_15(fn, params: Params) -> str:
        # hotfix, formalize tuples
        if len(params.asl) == 2 and isinstance(params.asl.first(), CLRList) and params.asl.first().type == "tuple":
            l_parts = [fn.apply(params.but_with(asl=child)) for child in params.asl.first()]
            r_parts = [fn.apply(params.but_with(asl=child)) for child in params.asl.second()]
            strs = [f"({params.asl.type} {l} {r})" for l, r in zip (l_parts, r_parts)]
            return " ".join(strs)

        if params.asl.second().type == "call":
            # TODO: remove this as this should never be the case.
            raise Exception("Not implemented in case of call")

        return f"(= {fn.transmute(params.asl.items(), params)})"

    @Wrangler.covers(asls_of_type("."))
    def partial_16(fn, params: Params) -> str:
        return f"(. {fn.transmute(params.asl.items(), params)})"
