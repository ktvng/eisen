from __future__ import annotations

from alpaca.clr import CLRList, CLRToken
from alpaca.utils import Wrangler, Formatter
from alpaca.concepts import Type, Context, Instance
from alpaca.validator import AbstractParams

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

class Params(AbstractParams):
    def __init__(self, 
            asl: CLRList, 
            mod: Context,
            global_mod: Context,
            as_ptr: bool,
            counter: SharedCounter,
            ):

        self.asl = asl
        self.mod = mod
        self.global_mod = global_mod
        self.as_ptr = as_ptr
        self.counter = counter

    def but_with(self,
            asl: CLRList = None,
            mod: Context = None,
            global_mod: Context = None,
            as_ptr: bool = None,
            counter: SharedCounter = None
            ):

        return self._but_with(asl=asl, mod=mod, global_mod=global_mod, as_ptr=as_ptr, counter=counter)

class CTransmutation(Wrangler):
    global_prefix = ""
    def run(self, asl: CLRList) -> str:
        txt = Formatter.format_clr(self.apply(Params(asl, asl.module, asl.module, False, SharedCounter(0))))
        return txt

    def apply(self, params: Params) -> str:
        return self._apply([params], [params])

    def asls_of_type(type: str, *args):
        def predicate(params: Params):
            return params.asl.type in list(args) + [type]
        return predicate

    # TESTING
    @Wrangler.default
    def default_(fn, params: Params) -> str:
        return f".{params.asl.type}"

    @classmethod
    def get_full_name(cls, instance: Instance) -> str:
        prefix = ""
        current_context = instance.context
        while current_context:
            prefix = f"{current_context.name}_" + prefix
            current_context = current_context.parent

        return f"{CTransmutation.global_prefix}{prefix}{instance.name}"        

    @classmethod
    def get_struct_name(cls, name: str, current_context: Context) -> str:
        prefix = ""
        while current_context:
            prefix = f"{current_context.name}_" + prefix
            current_context = current_context.parent

        return f"{CTransmutation.global_prefix}{prefix}{name}"        
    
    @classmethod
    def get_name_of_type(cls, type: Type) -> str:
        if type.is_novel():
            return type.name
        elif type.is_struct():
            return "struct_name"
        else:
            raise Exception(f"Unimplemented {type}")

    def transmute(fn, asls: list[CLRList], params: Params) -> str:
        return " ".join([fn.apply(params.but_with(asl=asl)) for asl in asls])

    # TODO: need to make this struct name by modules
    @Wrangler.covers(lambda params: isinstance(params.asl, CLRToken))
    def token_(fn, params: Params) -> str:
        return params.asl.value

    @Wrangler.covers(asls_of_type("start"))
    def partial_1(fn, params: Params) -> str:
        return f"(start {fn.transmute(params.asl.items(), params)})"

    @Wrangler.covers(asls_of_type("mod"))
    def partial_2(fn, params: Params) -> str:
        return f"{fn.transmute(params.asl.items()[1:], params)}"

    @Wrangler.covers(asls_of_type("struct"))
    def partial_3(fn, params: Params) -> str:
        full_name = CTransmutation.get_struct_name(params.asl.first().value, params.asl.module)
        attributes = [child for child in params.asl[1:] if child.type == ":"]
        attribute_strs = " ".join([fn.apply(params.but_with(asl=attr)) for attr in attributes])
        
        methods = [child for child in params.asl[1:] if child not in attributes]
        method_strs = " ".join([fn.apply(params.but_with(asl=meth)) for meth in methods])

        code = f"(struct {full_name} {attribute_strs}) {method_strs}"
        return code

    @Wrangler.covers(asls_of_type(
        "args", "seq", "+", "-", "*", "/", "<", ">", "<=", ">=", "==", "!=",
        "+=", "-=", "*=", "/=",
        "call", "params", "if", "while", "cond", "return"))
    def partial_4(fn, params: Params) -> str:
        return f"({params.asl.type} {fn.transmute(params.asl.items(), params)})"

    @Wrangler.covers(asls_of_type(":"))
    def partial_5(fn, params: Params) -> str:
        name = fn.apply(params.but_with(asl=params.asl.first()))
        type = fn.apply(params.but_with(asl=params.asl.second()))
        return f"(decl {type} {name})"

    # TODO make real type
    @Wrangler.covers(asls_of_type("type"))
    def partial_6(fn, params: Params) -> str:
        type: Type = params.asl.returns_type
        if params.as_ptr:
            return f"(type (ptr {CTransmutation.get_name_of_type(type)}))"
        return f"(type {CTransmutation.get_name_of_type(type)})"

    @Wrangler.covers(asls_of_type("prod_type"))
    def partial_7(fn, params: Params) -> str:
        return fn.transmute(params.asl.items(), params)

    @Wrangler.covers(asls_of_type("def"))
    def partial_8(fn, params: Params) -> str:
        name = CTransmutation.get_full_name(params.asl.instances[0])
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
        return f"({params.asl.type} {CTransmutation.get_full_name(params.asl.instances[0])})"

    @Wrangler.covers(asls_of_type("rets"))
    def partial_13(fn, params: Params) -> str:
        if not params.asl:
            return ""
        return fn.apply(params.but_with(asl=params.asl.first(), as_ptr=True))

    @Wrangler.covers(asls_of_type("ref"))
    def partial_14(fn, params: Params) -> str:
        if params.asl.instances[0].is_ptr:
            return f"({params.asl.type} (deref {fn.apply(params.but_with(asl=params.asl.first()))}))"
        return f"({params.asl.type} {fn.apply(params.but_with(asl=params.asl.first()))})"

    @Wrangler.covers(asls_of_type("="))
    def partial_15(fn, params: Params) -> str:
        if params.asl.second().type == "call":
            raise Exception("Not implemented in case of call")

        return f"(= {fn.transmute(params.asl.items(), params)})"

    @Wrangler.covers(asls_of_type(""))
    def partial_(fn, params: Params) -> str:
        pass

    @Wrangler.covers(asls_of_type(""))
    def partial_(fn, params: Params) -> str:
        pass
