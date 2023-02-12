from __future__ import annotations

import alpaca
from alpaca.utils import Visitor
from alpaca.clr import CLRList, CLRToken

binops = ["+", "-", "/", "*", "<", ">", "<=", ">=", "==", "!=", "+=", "-=", "/=", "*=", "="]

class Writer(Visitor):
    def run(self, asl: CLRList) -> str:
        p = self.apply(asl)
        txt = "".join(p)
        return alpaca.utils.formatter.indent(txt)

    def apply(self, asl: CLRList) -> list[str]:
        return self._route(asl, asl)

    @classmethod
    def apply_fn_to_all_children(cls, fn: Visitor, asl: CLRList) -> list[str]:
        if isinstance(asl, CLRToken):
            return fn.tokens_(fn, asl)
        p = []
        for child in asl:
            p += fn.apply(child)
        return p

    @Visitor.for_asls("start", "ref")
    def start_(fn, asl: CLRList):
        return Writer.apply_fn_to_all_children(fn, asl)

    @Visitor.for_asls("def")
    def def_(fn, asl: CLRList):
        return ["def ",
            *fn.apply(asl.first()),
            *fn.apply(asl.second()), ": ",
            *fn.apply(asl.third())]

    @Visitor.for_asls("args")
    def args_(fn, asl: CLRList):
        return ["(", *Writer.apply_fn_to_all_children(fn, asl), ")"]

    @Visitor.for_asls("tags", "tuple", "lvals")
    def tags_(fn, asl: CLRList):
        p = fn.apply(asl.first())
        for child in asl[1:]:
            p += [", "] + fn.apply(child)
        return p

    @staticmethod
    def write_sequential(fn, asl: CLRList, brackets: str):
        l, r = brackets[0], brackets[1]
        if asl.has_no_children():
            return [f"{l}{r}"]
        p = [f"{l}"] + fn.apply(asl.first())
        for child in asl[1:]:
            p += [", "] + fn.apply(child)
        return p + [f"{r}"]

    @Visitor.for_asls("params")
    def params_(fn, asl: CLRList):
        return Writer.write_sequential(fn, asl, "()")

    @Visitor.for_asls("list")
    def list_(fn, asl: CLRList):
        return Writer.write_sequential(fn, asl, "[]")

    @Visitor.for_asls("seq")
    def seq_(fn, asl: CLRList):
        p = ["\n{\n"]
        for child in asl:
            p += fn.apply(child) + ["\n"]
        p.append("}\n")
        return p

    @Visitor.for_asls("if")
    def if_(fn, asl: CLRList):
        p = ["if ", *fn.apply(asl.first())]
        for child in asl[1:]:
            if child.type == "cond":
                p.append("elif ")
            elif child.type == "seq":
                p.append("else: ")
            p += fn.apply(child)
        return p

    @Visitor.for_asls("while")
    def while_(fn, asl: CLRList):
        return ["while ", *fn.apply(asl.first())]

    @Visitor.for_asls("cond")
    def cond_(fn, asl: CLRList):
        return [*fn.apply(asl.first()), ": ", *fn.apply(asl.second())]

    @Visitor.for_asls("return")
    def return_(fn, asl: CLRList):
        return ["return ", *Writer.apply_fn_to_all_children(fn, asl)]

    @Visitor.for_asls(*binops)
    def binops_(fn, asl: CLRList):
        return [*fn.apply(asl.first()), f" {asl.type} ", *fn.apply(asl.second())]

    @Visitor.for_asls(".")
    def close_bind_(fn, asl: CLRList):
        return [*fn.apply(asl.first()), f"{asl.type}", *fn.apply(asl.second())]

    @Visitor.for_asls("init")
    def init_(fn, asl: CLRList):
        return ["def __init__", *fn.apply(asl.first()), ": ", *fn.apply(asl.second())]

    @Visitor.for_asls("class")
    def class_(fn, asl: CLRList):
        elems = []
        for child in asl[1:]:
            elems += fn.apply(child)
        return ["class ", *fn.apply(asl.first()), ": \n{\n", *elems, "}\n"]

    @Visitor.for_asls("vargs", "unpack")
    def unpack_(fn, asl: CLRList):
        return ["*", *fn.apply(asl.first())]

    @Visitor.for_asls("call")
    def call_(fn, asl: CLRList):
        return [*fn.apply(asl.first()), *fn.apply(asl.second())]

    @Visitor.for_tokens
    def tokens_(fn, asl: CLRList):
        if asl.type == "endl":
            return ["\n"]
        if asl.type == "str":
            return ['"', asl.value, '"']
        return [asl.value]

    @Visitor.for_default
    def default_(fn, asl: CLRList):
        print(f"Python Writer unimplemented for {asl}")
        return []
