from __future__ import annotations

import itertools
import re

from alpaca.utils import Visitor
from alpaca.parser import CommonBuilder
from alpaca.clr import ASTElements, AST, ASTToken
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
            components : ASTElements,
            *args) -> ASTElements:

        # EXPR . FUNCTION_CALL
        function_call = components[2]
        if not isinstance(function_call, AST):
            raise Exception("function call should be CLRList")

        params = function_call[1]
        params[:] = [components[0], *params]

        return function_call

    @CommonBuilder.for_procedure("handle_op_pref")
    def handle_op_pref(
            fn,
            config : Config,
            components : ASTElements,
            *args) -> ASTElements:

        flattened_comps = CommonBuilder.flatten_components(components)
        if len(flattened_comps) != 2:
            raise Exception(f"expected size 2 for handle_op_pref, got {flattened_comps}")

        return [AST(flattened_comps[0].value, [flattened_comps[1]], flattened_comps[0].line_number)]

class Writer(Visitor):
    def run(self, ast: AST) -> str:
        parts = Writer().apply(ast)
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

    def apply(self, ast: AST) -> list[str]:
        return self._route(ast, ast)

    def asts_of_type(types: str | list[str]):
        if isinstance(types, str):
            types = [types]
        def predicate(ast: AST):
            return ast.type in types
        return predicate

    def delegate(fn, ast: AST) -> list[str]:
        if ast:
            return list(itertools.chain(*[fn.apply(child) for child in ast]))
        return []

    @Visitor.for_tokens
    def token_(fn, ast: ASTToken) -> list[str]:
        if ast.type == "str":
            return ['"', ast.value, '"']
        return [ast.value]

    @Visitor.for_ast_types("!")
    def stop_(fn, ast: AST):
        return ["!", *fn.apply(ast.first())]

    @Visitor.for_ast_types("start")
    def start_(fn, ast: AST) -> list[str]:
        lists_for_components = [fn.apply(child) for child in ast]

        # filter out empty lists and add new lines
        lists_for_components = [l + ["\n"] for l in lists_for_components if l]
        return list(itertools.chain(*lists_for_components))

    @Visitor.for_ast_types("decl")
    def decl_(fn, ast: AST) -> list[str]:
        return [*fn.apply(ast.first()), " ", *fn.apply(ast.second())]

    @Visitor.for_ast_types("def")
    def def_(fn, ast: AST) -> list[str]:
        parts = [*fn.apply(ast.first()), " "]
        for child in ast[1:]:
            parts.extend(fn.apply(child))
        return parts

    @Visitor.for_ast_types("struct_decl")
    def struct_decl_(fn, ast: AST) -> list[str]:
        return ["struct ", *fn.apply(ast.first()), " ", *fn.apply(ast.second())]

    @Visitor.for_ast_types("type", "call", "fn", "ref")
    def pass_(fn, ast: AST) -> list[str]:
        return fn.delegate(ast)

    @Visitor.for_ast_types("cond")
    def cond_(fn, ast: AST) -> list[str]:
        return ["(", *fn.apply(ast.first()), ")", *fn.apply(ast.second())]

    @Visitor.for_ast_types("seq")
    def seq_(fn, ast: AST) -> list[str]:
        contexts = ["if", "while", "for"]
        components = []
        for child in ast:
            if child.type in contexts:
                components.append(fn.apply(child) + ["\n"])
            else:
                components.append(fn.apply(child) + [";\n"])
        return [" {\n"] + list(itertools.chain(*components)) + ["}\n"]

    @Visitor.for_ast_types("+", "-", "/", "*", "&&", "||", "<", ">", "<=", ">=", "=", "==", "!=", ".", "+=", "-=", "/=", "*=", "->")
    def op_(fn, ast: AST) -> list[str]:
        ops_which_dont_need_space = [".", "->"]
        op = ast.type if ast.type in ops_which_dont_need_space else f" {ast.type} "
        return [*fn.apply(ast.first()), op, *fn.apply(ast.second())]

    @Visitor.for_ast_types("ptr")
    def ptr_(fn, ast: AST) -> list[str]:
        return fn.delegate(ast) + ["*"]

    @Visitor.for_ast_types("return")
    def return_(fn, ast: AST) -> list[str]:
        return_value = fn.delegate(ast)
        if return_value:
            return ["return "] + return_value
        return ["return"]

    @Visitor.for_ast_types("params", "args")
    def params_(fn, ast: AST) -> list[str]:
        if not ast:
            return ["()"]
        parts = fn.apply(ast.first())
        for child in ast[1:]:
            parts += [", "] + fn.apply(child)
        return ["("] + parts + [")"]

    @Visitor.for_ast_types("while")
    def while_(fn, ast: AST) -> list[str]:
        return [f"while "] + fn.delegate(ast)

    @Visitor.for_ast_types("for")
    def for_(fn, ast: AST) -> list[str]:
        return ["for (",
                *fn.apply(ast.first()), "; ",
                *fn.apply(ast.second()), "; ",
                *fn.apply(ast.third()), ")"] + fn.apply((ast[-1]))

    @Visitor.for_ast_types("index")
    def index_(fn, ast: AST) -> list[str]:
        return [*fn.apply(ast.first()), "[", *fn.apply(ast.second()), "]"]

    @Visitor.for_ast_types("or")
    def or_(fn, ast: AST) -> list[str]:
        return fn.apply(ast.first()) + [" || "] + fn.apply(ast.second())

    @Visitor.for_ast_types("and")
    def and_(fn, ast: AST) -> list[str]:
        return fn.apply(ast.first()) + [" && "] + fn.apply(ast.second())

    @Visitor.for_ast_types("struct")
    def struct_(fn, ast: AST) -> list[str]:
        parts = [f"struct ", *fn.apply(ast.first()), " {\n"]
        for child in ast[1:]:
            parts += fn.apply(child) + [";\n"]
        return parts + ["};\n"]

    @Visitor.for_ast_types("if")
    def if_(fn, ast: AST) -> list[str]:
        parts = [f"{ast.type} "] + fn.apply(ast.first())
        for child in ast[1:]:
            if child.type == "cond":
                parts += ["else if "] + fn.apply(child)
            elif child.type == "seq":
                parts += ["else "] + fn.apply(child)
            else:
                raise Exception(f"if_ unknown type {child.type}")
        return parts

    @Visitor.for_ast_types("addr")
    def addr_(fn, ast: AST) -> list[str]:
        return ["&"] + fn.delegate(ast)

    @Visitor.for_ast_types("deref")
    def deref_(fn, ast: AST) -> list[str]:
        return ["*"] + fn.delegate(ast)

    @Visitor.for_ast_types("array_decl")
    def array_decl_(fn, ast: AST) -> list[str]:
        if len(ast) == 3:
            return fn.apply(ast.first()) + [" "] + fn.apply(ast.second()) + ["["] + fn.apply(ast.third()) + ["]"]
        else:
            return fn.apply(ast.first()) + [" "] + fn.apply(ast.second()) + ["[]"]
