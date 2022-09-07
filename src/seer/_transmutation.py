from __future__ import annotations

from alpaca.asts import CLRList, CLRToken
from alpaca.utils import TransformFunction
from alpaca.validator import AbstractParams, Context, Type, Instance
import re
import itertools

class Params(AbstractParams):
    def __init__(self, 
            asl: CLRList, 
            mod: Context,
            global_mod: Context,
            ):

        self.asl = asl
        self.mod = mod
        self.global_mod = global_mod

    def but_with(self,
            asl: CLRList = None,
            mod: Context = None,
            global_mod: Context = None,
            ):

        return self._but_with(asl=asl, mod=mod, global_mod=global_mod)

def get_chunk_before_paren(clr: str) -> tuple[str, str]:
    first = clr.index("(")
    if first is not None:
        idx = clr.index("(", first+1)
    else:
        idx = None

    if idx is None:
        return clr, ""
    return clr[:idx], clr[idx:]

def get_clr_chunk(clr: str) -> tuple[str, str]:
    counter = 0
    ignore = False
    in_str = False

    for i, c in enumerate(clr):
        if c == "\\" and in_str:
            ignore = True
            continue

        if ignore and in_str:
            ignore = False
            continue

        if c == '"' and in_str:
            in_str = False
            continue

        if c == '"' and not in_str:
            in_str = True
            continue

        if c == "(":
            counter += 1
        elif c == ")":
            counter -= 1
        
        if counter == 0:
            if i+1 == len(clr):
                return clr, ""
            return clr[:i+1], clr[i+1:]


    return clr, ""

def count_parens(clr: str) -> int:
    counter = 0
    for c in clr:
        if c == "(":
            counter += 1
        elif c == ")":
            counter -= 1
    return counter
        
 
def indent_clr(clr: str) -> str:
    original = clr
    formatted = ""
    indent = "  "
    indent_level = 0
    while clr:
        flush = 0
        while flush< len(clr) and (clr[flush] != "("):
            flush += 1

        if flush:
            flushed, rest = clr[:flush], clr[flush:]

            formatted += indent * indent_level + flushed + "\n"
            clr = rest

        chunk, rest = get_clr_chunk(clr)
        if len(chunk) > 64:
            head, rest = get_chunk_before_paren(clr)
            formatted += indent * indent_level + head
            clr = rest
            indent_level += 1
        else:
            indent_level += count_parens(chunk)
            formatted += indent * indent_level + chunk
            clr = rest

        more = 0
        while more < len(clr) and (clr[more] == " " or clr[more] == ")"):
            if clr[more] == ")":
                indent_level -= 1
            more += 1

        some_more, rest = clr[:more], clr[more:]
        formatted += some_more + "\n"
        clr = rest

    return formatted


class CTransmutation(TransformFunction):
    global_prefix = ""
    def run(self, asl: CLRList) -> str:
        return indent_clr(self.apply(Params(asl, asl.module, asl.module)))

    def apply(self, params: Params) -> str:
        return self._apply([params], [params])

    def asls_of_type(type: str, *args):
        def predicate(params: Params):
            return params.asl.type in list(args) + [type]
        return predicate

    # TESTING
    @TransformFunction.default
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
    @TransformFunction.covers(lambda params: isinstance(params.asl, CLRToken))
    def token_(fn, params: Params) -> str:
        return params.asl.value

    @TransformFunction.covers(asls_of_type("start"))
    def partial_1(fn, params: Params) -> str:
        return f"(start {fn.transmute(params.asl.items(), params)})"

    @TransformFunction.covers(asls_of_type("mod"))
    def partial_2(fn, params: Params) -> str:
        return f"{fn.transmute(params.asl.items()[1:], params)}"

    @TransformFunction.covers(asls_of_type("struct"))
    def partial_3(fn, params: Params) -> str:
        full_name = CTransmutation.get_struct_name(params.asl.first().value, params.asl.module)
        attributes = [child for child in params.asl[1:] if child.type == ":"]
        attribute_strs = " ".join([fn.apply(params.but_with(asl=attr)) for attr in attributes])
        
        methods = [child for child in params.asl[1:] if child not in attributes]
        method_strs = " ".join([fn.apply(params.but_with(asl=meth)) for meth in methods])

        code = f"(struct {full_name} {attribute_strs}) {method_strs}"
        return code

    @TransformFunction.covers(asls_of_type(
        "args", "seq", "+", "-", "*", "/", "<", ">", "<=", ">=", "=", "==", "!=",
        "+=", "-=", "*=", "/=",
        "ref", "call", "params", "if", "while", "cond", "return"))
    def partial_4(fn, params: Params) -> str:
        return f"({params.asl.type} {fn.transmute(params.asl.items(), params)})"

    @TransformFunction.covers(asls_of_type(":"))
    def partial_5(fn, params: Params) -> str:
        name = fn.apply(params.but_with(asl=params.asl.first()))
        type = fn.apply(params.but_with(asl=params.asl.second()))
        return f"(decl {type} {name})"

    # TODO make real type
    @TransformFunction.covers(asls_of_type("type"))
    def partial_6(fn, params: Params) -> str:
        type: Type = params.asl.returns_type
        return f"(type {CTransmutation.get_name_of_type(type)})"

    @TransformFunction.covers(asls_of_type("prod_type"))
    def partial_7(fn, params: Params) -> str:
        return fn.transmute(params.asl.items(), params)

    @TransformFunction.covers(asls_of_type("def"))
    def partial_8(fn, params: Params) -> str:
        name = CTransmutation.get_full_name(params.asl.instances[0])
        return f"(def (type void) {name} {fn.transmute(params.asl.items()[1:], params)})"

    @TransformFunction.covers(asls_of_type("let"))
    def partial_9(fn, params: Params) -> str:
        return fn.apply(params.but_with(asl=params.asl.first()))

    @TransformFunction.covers(asls_of_type("ilet"))
    def partial_(fn, params: Params) -> str:
        pass 

    @TransformFunction.covers(asls_of_type("::"))
    def partial_11(fn, params: Params) -> str:
        return fn.apply(params.but_with(asl=params.asl.second()))

    @TransformFunction.covers(asls_of_type("fn"))
    def partial_12(fn, params: Params) -> str:
        if (params.asl.first().value == "print"):
            return f"(fn print)"
        return f"({params.asl.type} {CTransmutation.get_full_name(params.asl.instances[0])})"

    @TransformFunction.covers(asls_of_type("rets"))
    def partial_(fn, params: Params) -> str:
        pass

    @TransformFunction.covers(asls_of_type(""))
    def partial_(fn, params: Params) -> str:
        pass

    @TransformFunction.covers(asls_of_type(""))
    def partial_(fn, params: Params) -> str:
        pass

    @TransformFunction.covers(asls_of_type(""))
    def partial_(fn, params: Params) -> str:
        pass

    @TransformFunction.covers(asls_of_type(""))
    def partial_(fn, params: Params) -> str:
        pass
