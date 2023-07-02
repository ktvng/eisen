from __future__ import annotations

import alpaca
from alpaca.clr import CLRList, CLRToken
from alpaca.utils import Visitor

import eisen.adapters as adapters

class Writer(Visitor):
    def run(self, asl: CLRList) -> str:
        parts = self.apply(asl)
        raw_text = "".join(parts)
        return alpaca.utils.formatter.indent(raw_text)

    def apply(self, asl: CLRList) -> list[str]:
        return self._route(asl, asl)

    @Visitor.for_tokens
    def token_(fn, asl: CLRToken):
        if asl.type == "str":
            return ['"', asl.value, '"']
        return [asl.value]

    @Visitor.for_asls("start")
    def start_(fn, asl: CLRList):
        parts = []
        for child in asl:
            parts += fn.apply(child) + ["\n"]
        return parts

    @Visitor.for_asls("struct")
    def struct_(fn, asl: CLRList):
        parts = ["struct ", *fn.apply(asl.first()), " {\n"]
        for child in asl[1:]:
            parts += fn.apply(child) + ["\n"]
        return parts + ["}\n"]

    @Visitor.for_asls("variant")
    def variant_(fn, asl: CLRList):
        parts = ["variant ",
            *fn.apply(asl.first()),
            " of ",
            *fn.apply(asl.second()),
            " {\n"]

        for child in asl[2:]:
            parts += fn.apply(child) + ["\n"]
        return parts + ["}\n"]

    @Visitor.for_asls("mod")
    def mod_(fn, asl: CLRList):
        parts = ["mod ",
            *fn.apply(asl.first()),
            " {\n"]
        for child in asl[1:]:
            parts += fn.apply(child) + ["\n"]
        parts += ["}\n"]
        return parts

    @Visitor.for_asls(":")
    def colon_(fn, asl: CLRList):
        return [*fn.apply(asl.first()),
            ": ",
            *fn.apply(asl.second())]

    @Visitor.for_asls("create")
    def create_(fn, asl: CLRList):
        return ["create(",
            *fn.apply(asl.second()),
            ") -> ",
            *fn.apply(asl.third()),
            *fn.apply(asl[-1])]

    @Visitor.for_asls("is_fn")
    def is_fn(fn, asl: CLRList):
        return ["is(",
            *fn.apply(asl.second()),
            ") -> ",
            *fn.apply(asl.third()),
            *fn.apply(asl[-1])]

    @Visitor.for_asls("type", "fn_type_in", "fn_type_out", "ref", "fn", *adapters.ArgsRets.asl_types)
    def pass_(fn, asl: CLRList):
        if not asl:
            return []
        return fn.apply(asl.first())

    @Visitor.for_asls("prod_type", "params")
    def prod_type(fn, asl: CLRList):
        parts = []
        if asl:
            parts += fn.apply(asl.first())
        for child in asl[1:]:
            parts += [", ", *fn.apply(child)]
        return parts

    @Visitor.for_asls("def")
    def def_(fn, asl: CLRList):
        return_value = fn.apply(asl.third())
        return_statement_parts = []
        if return_value:
            return_statement_parts = [" ->"] + return_value
        return ["fn ",
            *fn.apply(asl.first()),
            "(",
            *fn.apply(asl.second()),
            ") ",
            *return_statement_parts,
            *fn.apply(asl[-1])]

    @Visitor.for_asls("fn_type")
    def fn_type_(fn, asl: CLRList):
        return ["(",
            *fn.apply(asl.first()),
            ") -> ",
            *fn.apply(asl.second())]

    @Visitor.for_asls("imut", "ilet")
    def ilet(fn, asl: CLRList):
        decl = asl.type[1:]
        return [decl, " ", *fn.apply(asl.first()), " = ", *fn.apply(asl.second())]

    @Visitor.for_asls("let", "mut", "val")
    def let_(fn, asl: CLRList):
        decl = asl.type
        return [decl, " ", *fn.apply(asl.first())]

    @Visitor.for_asls("while")
    def while_(fn, asl: CLRList):
        return ["while ", *fn.apply(asl.first())]

    @Visitor.for_asls("cast")
    def cast_(fn, asl: CLRList):
        return [
            *fn.apply(asl.first()),
            ".as(",
            *fn.apply(asl.second()),
            ")"]

    @Visitor.for_asls("seq")
    def seq_(fn, asl: CLRList):
        parts = []
        for child in asl:
            parts += fn.apply(child) + ["\n"]
        return ["{\n", *parts, "}\n"]

    @Visitor.for_asls("cond")
    def cond_(fn, asl: CLRList):
        return ["(", *fn.apply(asl.first()), ") ", *fn.apply(asl.second())]

    @Visitor.for_asls("<", ">", "<=", ">=", "+", "-", "/", "*", "+=", "=", "==", ".", "::", "and", "or")
    def bin_op_(fn, asl: CLRList):
        if asl.type in [".", "::"]:
            operator = asl.type
        else:
            operator = f" {asl.type} "
        return [*fn.apply(asl.first()), operator, *fn.apply(asl.second())]

    @Visitor.for_asls("call")
    def call_(fn, asl: CLRList):
        return [*fn.apply(asl.first()), "(", *fn.apply(asl.second()), ")"]

    @Visitor.for_asls("is_call")
    def is_call_(fn, asl: CLRList):
        name = asl.first().first().value[3:]
        return [*fn.apply(asl.second()), " is ", name]

    # TODO: need to work with elseif
    @Visitor.for_asls("if")
    def if_(fn, asl: CLRList):
        return ["if ", *fn.apply(asl.first())]

    @Visitor.for_asls("return")
    def return_(fn, asl: CLRList):
        return ["return"]
