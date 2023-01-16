from __future__ import annotations

import itertools
import re

from alpaca.utils import Visitor
from alpaca.parser import CommonBuilder
from alpaca.clr import CLRRawList, CLRList, CLRToken
from alpaca.config import Config
import alpaca.utils

class Callback(alpaca.lexer.AbstractCallback):
    @classmethod
    def string(cls, string : str) -> str:
        return string.replace('\\n', '\n')[1 : -1]

    @classmethod
    def str(cls, string : str) -> str:
        return string.replace('\\n', '\n')[1 : -1]


class Builder(CommonBuilder):
    @CommonBuilder.for_procedure("handle_call")
    def handle_call(
            fn,
            config : Config,
            components : CLRRawList,
            *args) -> CLRRawList:

        # EXPR . FUNCTION_CALL
        function_call = components[2]
        if not isinstance(function_call, CLRList):
            raise Exception("function call should be CLRList")

        params = function_call[1]
        params[:] = [components[0], *params]

        return function_call

    @CommonBuilder.for_procedure("handle_op_pref")
    def handle_op_pref(
            fn,
            config : Config,
            components : CLRRawList,
            *args) -> CLRRawList:

        flattened_comps = CommonBuilder.flatten_components(components)
        if len(flattened_comps) != 2:
            raise Exception(f"expected size 2 for handle_op_pref, got {flattened_comps}")

        return [CLRList(flattened_comps[0], [flattened_comps[1]], flattened_comps[0].line_number)]

class Writer(Visitor):
    def run(self, asl: CLRList) -> str:
        parts = Writer().apply(asl)
        txt = "".join(parts)
        txt = alpaca.utils.formatter.indent(txt)
        return Writer.filter_extraneous_newlines(txt)

    @classmethod
    def filter_extraneous_newlines(self, txt: str) -> str:
        prev_line_empty = False

        filtered_txt = ""
        for line in txt.split("\n"):
            if not line.strip():
                prev_line_empty = True
                continue
            if prev_line_empty:
                if not re.match(r" *} *$", line):
                    filtered_txt += "\n"
                prev_line_empty = False
            filtered_txt += line + "\n"
        return filtered_txt

    def apply(self, asl: CLRList) -> list[str]:
        return self._route(asl, asl)

    def asls_of_type(types: str | list[str]):
        if isinstance(types, str):
            types = [types]
        def predicate(asl: CLRList):
            return asl.type in types
        return predicate

    def delegate(fn, asl: CLRList) -> list[str]:
        if asl:
            return list(itertools.chain(*[fn.apply(child) for child in asl]))
        return []

    @Visitor.for_tokens
    def token_(fn, asl: CLRToken) -> list[str]:
        return [asl.value]

    @Visitor.for_asls("start")
    def start_(fn, asl: CLRList) -> list[str]:
        lists_for_components = [fn.apply(child) for child in asl]

        # filter out empty lists and add new lines
        lists_for_components = [l + ["\n"] for l in lists_for_components if l]
        return list(itertools.chain(*lists_for_components))

    @Visitor.for_asls("decl")
    def decl_(fn, asl: CLRList) -> list[str]:
        return [*fn.apply(asl.first()), " ", *fn.apply(asl.second())]

    @Visitor.for_asls("def")
    def def_(fn, asl: CLRList) -> list[str]:
        parts = [*fn.apply(asl.first()), " "]
        for child in asl[1:]:
            parts.extend(fn.apply(child))
        return parts

    @Visitor.for_asls("struct_decl")
    def struct_decl_(fn, asl: CLRList) -> list[str]:
        return ["struct ", *fn.apply(asl.first()), " ", *fn.apply(asl.second())]

    @Visitor.for_asls("type", "call", "fn", "ref")
    def pass_(fn, asl: CLRList) -> list[str]:
        return fn.delegate(asl)

    @Visitor.for_asls("cond")
    def cond_(fn, asl: CLRList) -> list[str]:
        return ["(", *fn.apply(asl.first()), ")", *fn.apply(asl.second())]

    @Visitor.for_asls("seq")
    def seq_(fn, asl: CLRList) -> list[str]:
        contexts = ["if", "while"]
        components = []
        for child in asl:
            if child.type in contexts:
                components.append(fn.apply(child) + ["\n"])
            else:
                components.append(fn.apply(child) + [";\n"])
        return [" {\n"] + list(itertools.chain(*components)) + ["}\n"]

    @Visitor.for_asls("+", "-", "/", "*", "&&", "||", "<", ">", "<=", ">=", "=", "==", "!=", ".", "+=", "-=", "/=", "*=", "->")
    def op_(fn, asl: CLRList) -> list[str]:
        ops_which_dont_need_space = [".", "->"]
        op = asl.type if asl.type in ops_which_dont_need_space else f" {asl.type} "
        return [*fn.apply(asl.first()), op, *fn.apply(asl.second())]

    @Visitor.for_asls("ptr")
    def ptr_(fn, asl: CLRList) -> list[str]:
        return fn.delegate(asl) + ["*"]

    @Visitor.for_asls("return")
    def return_(fn, asl: CLRList) -> list[str]:
        return_value = fn.delegate(asl)
        if return_value:
            return ["return "] + return_value
        return ["return"]

    @Visitor.for_asls("params", "args")
    def params_(fn, asl: CLRList) -> list[str]:
        if not asl:
            return ["()"]
        parts = fn.apply(asl.first())
        for child in asl[1:]:
            parts += [", "] + fn.apply(child)
        return ["("] + parts + [")"]

    @Visitor.for_asls("while")
    def while_(fn, asl: CLRList) -> list[str]:
        return [f"while "] + fn.delegate(asl)

    @Visitor.for_asls("struct")
    def struct_(fn, asl: CLRList) -> list[str]:
        parts = [f"struct ", *fn.apply(asl.first()), " {\n"]
        for child in asl[1:]:
            parts += fn.apply(child) + [";\n"]
        return parts + ["};\n"]

    @Visitor.for_asls("if")
    def if_(fn, asl: CLRList) -> list[str]:
        parts = [f"{asl.type} "] + fn.apply(asl.first())
        for child in asl[1:]:
            if child.type == "cond":
                parts += ["else if "] + fn.apply(child)
            elif child.type == "seq":
                parts += ["else "] + fn.apply(child)
            else:
                raise Exception(f"if_ unknown type {child.type}")
        return parts

    @Visitor.for_asls("addr")
    def addr_(fn, asl: CLRList) -> list[str]:
        return ["&"] + fn.delegate(asl)

    @Visitor.for_asls("deref")
    def deref_(fn, asl: CLRList) -> list[str]:
        return ["*"] + fn.delegate(asl)
