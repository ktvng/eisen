from __future__ import annotations

import alpaca
from alpaca.clr import CLRList
from alpaca.utils import Visitor

from eisen.common._common import Utils

from eisen.common.state import State

class CTransmutation(Visitor):
    global_prefix = ""
    def run(self, asl: CLRList, state: State) -> str:
        txt = alpaca.utils.formatter.format_clr(self.apply(state))
        return txt

    def apply(self, params: State) -> str:
        if self.debug and isinstance(params.asl, CLRList):
            print("\n"*64)
            print(params.inspect())
            print("\n"*4)
            input()
        return self._route(params.asl, params)

    # TESTING
    @Visitor.for_default
    def default_(fn, params: State) -> str:
        return f"#{params.asl.type}"

    @classmethod
    def _main_method(cls) -> str:
        return "(def (type int) main (args ) (seq (call (fn _main) (params )) (return 0)))"

    def transmute(fn, asls: list[CLRList], params: State) -> str:
        return " ".join([fn.apply(params.but_with(asl=asl)) for asl in asls])

    # TODO: need to make this struct name by modules
    @Visitor.for_tokens
    def token_(fn, params: State) -> str:
        if params.asl.type == "str":
            return '"' + params.asl.value + '"'
        return params.asl.value

    @Visitor.for_asls("start")
    def partial_1(fn, params: State) -> str:
        return f"(start {fn.transmute(params.asl.items(), params)} {fn._main_method()})"

    @Visitor.for_asls("mod")
    def partial_2(fn, params: State) -> str:
        return f"{fn.transmute(params.asl.items()[1:], params)}"

    @Visitor.for_asls("struct")
    def partial_3(fn, params: State) -> str:
        full_name = Utils.get_full_name_of_struct(
            name=params.asl.first().value,
            mod=params.get_enclosing_module())
        attributes = [child for child in params.asl[1:] if child.type == ":"]
        attribute_strs = " ".join([fn.apply(params.but_with(asl=attr)) for attr in attributes])

        methods = [child for child in params.asl[1:] if child not in attributes]
        method_strs = " ".join([fn.apply(params.but_with(asl=meth)) for meth in methods])

        code = f"(struct {full_name} {attribute_strs}) {method_strs}"
        return code

    @Visitor.for_asls(
        "args", "seq", "+", "-", "*", "/", "<", ">", "<=", ">=", "==", "!=",
        "+=", "-=", "*=", "/=",
        "params", "if", "while", "cond", "return", "call")
    def partial_4(fn, params: State) -> str:
        return f"({params.asl.type} {fn.transmute(params.asl.items(), params)})"

    @Visitor.for_asls(":")
    def partial_5(fn, params: State) -> str:
        # hotfix, formalize tuples
        if (isinstance(params.asl.first(), CLRList) and params.asl.first().type == "tags"
            and params.asl.second().type == "type"):
            names = [token.value for token in params.asl.first()]
        else:
            names = [fn.apply(params.but_with(asl=params.asl.first()))]

        type = fn.apply(params.but_with(asl=params.asl.second()))
        strs = []
        for name in names:
            if params.but_with_second_child().get_returned_type().is_struct():
                strs.append(f"(struct_decl {type} {name})")
            else:
                strs.append(f"(decl {type} {name})")
        return " ".join(strs)

    # TODO make real type
    @Visitor.for_asls("type")
    def partial_6(fn, params: State) -> str:
        type = params.get_returned_type()
        mod = params.get_enclosing_module()
        if params.as_ptr:
            return f"(type (ptr {Utils.get_name_of_type(type, mod)}))"
        return f"(type {Utils.get_name_of_type(type, mod)})"

    @Visitor.for_asls("prod_type")
    def partial_7(fn, params: State) -> str:
        return fn.transmute(params.asl.items(), params)

    @Visitor.for_asls("def")
    def partial_8(fn, params: State) -> str:
        instance = params.get_instances()[0]
        name = instance.get_c_name()
        args = fn.apply(params.but_with(asl=params.asl.second()))
        rets = fn.apply(params.but_with(asl=params.asl.third()))
        seq = fn.apply(params.but_with(asl=params.asl[-1]))
        signature = args[:-1] + rets + ")"
        return f"(def (type void) {name} {signature} {seq})"

    @Visitor.for_asls("create")
    def partial_17(fn, params: State) -> str:
        instances = params.get_instances()
        # get the type returned by the create object, as this is the type of the struct.
        name = instances[0].get_c_name() + "_constructor"
        args = fn.apply(params.but_with(asl=params.asl.second()))
        rets = fn.apply(params.but_with(asl=params.asl.third()))
        seq = fn.apply(params.but_with(asl=params.asl[-1]))
        signature = args[:-1] + rets + ")"
        return f"(def (type void) {name} {signature} {seq})"

    @Visitor.for_asls("let")
    def partial_9(fn, params: State) -> str:
        return fn.apply(params.but_with(asl=params.asl.first()))

    @Visitor.for_asls("ilet")
    def partial_(fn, params: State) -> str:
        instance = params.get_instances()[0]
        mod = params.get_enclosing_module()
        type_name = Utils.get_name_of_type(instance.type, mod)
        name = params.asl.first().value
        value = fn.apply(params.but_with(asl=params.asl.second()))
        if instance.type.is_struct():
            return f"(struct_decl (type {type_name}) {name}) (= {name} {value})"
        return f"(decl (type {type_name}) {name}) (= {name} {value})"

    @Visitor.for_asls("::")
    def partial_11(fn, params: State) -> str:
        return fn.apply(params.but_with(asl=params.asl.second()))

    @Visitor.for_asls("rets")
    def partial_13(fn, params: State) -> str:
        if not params.asl:
            return ""
        return fn.apply(params.but_with(asl=params.asl.first(), as_ptr=True))

    @Visitor.for_asls("ref")
    def partial_14(fn, params: State) -> str:
        if (params.asl.first().value == "print"):
            return f"(fn printf)"

        instances = params.get_instances()
        if instances[0].is_ptr:
            return f"(deref (ref {fn.apply(params.but_with(asl=params.asl.first()))}))"
        return f"(ref {fn.apply(params.but_with(asl=params.asl.first()))})"

    @Visitor.for_asls("=")
    def partial_15(fn, params: State) -> str:
        # hotfix, formalize tuples
        if len(params.asl) == 2 and isinstance(params.asl.first(), CLRList) and params.asl.first().type == "tuple":
            l_parts = [fn.apply(params.but_with(asl=child)) for child in params.asl.first()]
            r_parts = [fn.apply(params.but_with(asl=child)) for child in params.asl.second()]
            strs = [f"({params.asl.type} {l} {r})" for l, r in zip (l_parts, r_parts)]
            return " ".join(strs)

        return f"(= {fn.transmute(params.asl.items(), params)})"

    @Visitor.for_asls(".")
    def partial_16(fn, params: State) -> str:
        return f"(. {fn.transmute(params.asl.items(), params)})"
