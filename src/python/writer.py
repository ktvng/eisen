from __future__ import annotations

import alpaca
from alpaca.utils import Visitor
from alpaca.clr import AST, ASTToken

binops = ["+", "-", "/", "*", "<", ">", "<=", ">=",
    "==", "!=", "+=", "-=", "/=", "*=",
    "=",
    "//=", "//",
    "and", "or"
]

class Writer(Visitor):
    def run(self, ast: AST) -> str:
        p = self.apply(ast)
        txt = "".join(p)
        return alpaca.utils.formatter.indent(txt)

    def apply(self, ast: AST) -> list[str]:
        return self._route(ast, ast)

    @classmethod
    def apply_fn_to_all_children(cls, fn: Visitor, ast: AST) -> list[str]:
        if isinstance(ast, ASTToken):
            return fn.tokens_(fn, ast)
        p = []
        for child in ast:
            p += fn.apply(child)
        return p

    @Visitor.for_ast_types("start", "ref")
    def start_(fn, ast: AST):
        return Writer.apply_fn_to_all_children(fn, ast)

    @Visitor.for_ast_types("def")
    def def_(fn, ast: AST):
        return ["def ",
            *fn.apply(ast.first()),
            *fn.apply(ast.second()), ": ",
            *fn.apply(ast.third())]

    @Visitor.for_ast_types("args")
    def args_(fn, ast: AST):
        if ast.has_no_children():
            return ["()"]
        p = ["("] + fn.apply(ast.first())
        for child in ast[1:]:
            p += [", "] + fn.apply(child)
        return p + [")"]

    @Visitor.for_ast_types("tags", "tuple", "lvals")
    def tags_(fn, ast: AST):
        p = fn.apply(ast.first())
        for child in ast[1:]:
            p += [", "] + fn.apply(child)
        return p

    @staticmethod
    def write_sequential(fn, ast: AST, brackets: str):
        l, r = brackets[0], brackets[1]
        if ast.has_no_children():
            return [f"{l}{r}"]
        p = [f"{l}"] + fn.apply(ast.first())
        for child in ast[1:]:
            p += [", "] + fn.apply(child)
        return p + [f"{r}"]

    @Visitor.for_ast_types("params")
    def params_(fn, ast: AST):
        return Writer.write_sequential(fn, ast, "()")

    @Visitor.for_ast_types("list")
    def list_(fn, ast: AST):
        return Writer.write_sequential(fn, ast, "[]")

    @Visitor.for_ast_types("seq")
    def seq_(fn, ast: AST):
        p = ["\n{\n"]
        for child in ast:
            p += fn.apply(child) + ["\n"]
        p.append("}\n")
        return p

    @Visitor.for_ast_types("subseq")
    def subseq_(fn, ast: AST):
        p = []
        for child in ast:
            p += fn.apply(child) + ["\n"]
        return p

    @Visitor.for_ast_types("if")
    def if_(fn, ast: AST):
        p = ["if ", *fn.apply(ast.first())]
        for child in ast[1:]:
            if child.type == "cond":
                p.append("elif ")
            elif child.type == "seq":
                p.append("else: ")
            p += fn.apply(child)
        return p

    @Visitor.for_ast_types("while")
    def while_(fn, ast: AST):
        return ["while ", *fn.apply(ast.first())]

    @Visitor.for_ast_types("for")
    def for_(fn, ast: AST):
        return ["for ", ast.first().value, " in ", *fn.apply(ast.second()), ":",
            *fn.apply(ast.third())]

    @Visitor.for_ast_types("cond")
    def cond_(fn, ast: AST):
        return [*fn.apply(ast.first()), ": ", *fn.apply(ast.second())]

    @Visitor.for_ast_types("return")
    def return_(fn, ast: AST):
        return ["return ", *Writer.apply_fn_to_all_children(fn, ast)]

    @Visitor.for_ast_types(*binops)
    def binops_(fn, ast: AST):
        return [*fn.apply(ast.first()), f" {ast.type} ", *fn.apply(ast.second())]

    @Visitor.for_ast_types("not")
    def not_(fn ,ast: AST):
        return ["not ", *fn.apply(ast.first())]

    @Visitor.for_ast_types(".")
    def close_bind_(fn, ast: AST):
        return [*fn.apply(ast.first()), f"{ast.type}", *fn.apply(ast.second())]

    @Visitor.for_ast_types("init")
    def init_(fn, ast: AST):
        return ["def __init__", *fn.apply(ast.first()), ": ", *fn.apply(ast.second())]

    @Visitor.for_ast_types("class")
    def class_(fn, ast: AST):
        elems = []
        for child in ast[1:]:
            elems += fn.apply(child)
        return ["class ", *fn.apply(ast.first()), ": \n{\n", *elems, "}\n"]

    @Visitor.for_ast_types("vargs", "unpack")
    def unpack_(fn, ast: AST):
        return ["*", *fn.apply(ast.first())]

    @Visitor.for_ast_types("call")
    def call_(fn, ast: AST):
        return [*fn.apply(ast.first()), *fn.apply(ast.second())]

    @Visitor.for_ast_types("named")
    def named_(fn, ast: AST):
        return [*fn.apply(ast.first()), "=", *fn.apply(ast.second())]

    @Visitor.for_ast_types("index")
    def index_(fn, ast: AST):
        return [*fn.apply(ast.first()), "[", *fn.apply(ast.second()), "]"]

    @Visitor.for_tokens
    def tokens_(fn, ast: AST):
        if ast.type == "endl":
            return ["\n"]
        if ast.type == "str":
            return ['"', ast.value, '"']
        return [ast.value]

    @Visitor.for_ast_types("no_content")
    def no_content(fn, ast: AST):
        return []

    @Visitor.for_default
    def default_(fn, ast: AST):
        print(f"Python Writer unimplemented for {ast}")
        return []
