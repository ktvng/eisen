from __future__ import annotations

import alpaca
from alpaca.clr import AST, ASTToken
from alpaca.utils import Visitor

import eisen.adapters as adapters

class Writer(Visitor):
    def run(self, ast: AST) -> str:
        parts = self.apply(ast)
        raw_text = "".join(parts)
        return alpaca.utils.formatter.indent(raw_text)

    def apply(self, ast: AST) -> list[str]:
        return self._route(ast, ast)

    @Visitor.for_tokens
    def token_(fn, ast: ASTToken):
        if ast.type == "str":
            return ['"', ast.value, '"']
        return [ast.value]

    @Visitor.for_ast_types("start")
    def start_(fn, ast: AST):
        parts = []
        for child in ast:
            parts += fn.apply(child) + ["\n"]
        return parts

    @Visitor.for_ast_types("struct")
    def struct_(fn, ast: AST):
        parts = ["struct ", *fn.apply(ast.first()), " {\n"]
        for child in ast[1:]:
            parts += fn.apply(child) + ["\n"]
        return parts + ["}\n"]

    @Visitor.for_ast_types("mod")
    def mod_(fn, ast: AST):
        parts = ["mod ",
            *fn.apply(ast.first()),
            " {\n"]
        for child in ast[1:]:
            parts += fn.apply(child) + ["\n"]
        parts += ["}\n"]
        return parts

    @Visitor.for_ast_types(":")
    def colon_(fn, ast: AST):
        return [*fn.apply(ast.first()),
            ": ",
            *fn.apply(ast.second())]

    @Visitor.for_ast_types("create")
    def create_(fn, ast: AST):
        return ["create(",
            *fn.apply(ast.second()),
            ") -> ",
            *fn.apply(ast.third()),
            *fn.apply(ast[-1])]

    @Visitor.for_ast_types("is_fn")
    def is_fn(fn, ast: AST):
        return ["is(",
            *fn.apply(ast.second()),
            ") -> ",
            *fn.apply(ast.third()),
            *fn.apply(ast[-1])]

    @Visitor.for_ast_types("type", "fn_type_in", "fn_type_out", "ref", "fn", *adapters.ArgsRets.ast_types)
    def pass_(fn, ast: AST):
        if not ast:
            return []
        return fn.apply(ast.first())

    @Visitor.for_ast_types("prod_type", "params")
    def prod_type(fn, ast: AST):
        parts = []
        if ast:
            parts += fn.apply(ast.first())
        for child in ast[1:]:
            parts += [", ", *fn.apply(child)]
        return parts

    @Visitor.for_ast_types("def")
    def def_(fn, ast: AST):
        return_value = fn.apply(ast.third())
        return_statement_parts = []
        if return_value:
            return_statement_parts = [" ->"] + return_value
        return ["fn ",
            *fn.apply(ast.first()),
            "(",
            *fn.apply(ast.second()),
            ") ",
            *return_statement_parts,
            *fn.apply(ast[-1])]

    @Visitor.for_ast_types("fn_type")
    def fn_type_(fn, ast: AST):
        return ["(",
            *fn.apply(ast.first()),
            ") -> ",
            *fn.apply(ast.second())]

    @Visitor.for_ast_types("imut", "ilet")
    def ilet(fn, ast: AST):
        decl = ast.type[1:]
        return [decl, " ", *fn.apply(ast.first()), " = ", *fn.apply(ast.second())]

    @Visitor.for_ast_types("let", "mut", "val")
    def let_(fn, ast: AST):
        decl = ast.type
        return [decl, " ", *fn.apply(ast.first())]

    @Visitor.for_ast_types("while")
    def while_(fn, ast: AST):
        return ["while ", *fn.apply(ast.first())]

    @Visitor.for_ast_types("cast")
    def cast_(fn, ast: AST):
        return [
            *fn.apply(ast.first()),
            ".as(",
            *fn.apply(ast.second()),
            ")"]

    @Visitor.for_ast_types("seq")
    def seq_(fn, ast: AST):
        parts = []
        for child in ast:
            parts += fn.apply(child) + ["\n"]
        return ["{\n", *parts, "}\n"]

    @Visitor.for_ast_types("cond")
    def cond_(fn, ast: AST):
        return ["(", *fn.apply(ast.first()), ") ", *fn.apply(ast.second())]

    @Visitor.for_ast_types("<", ">", "<=", ">=", "+", "-", "/", "*", "+=", "=", "==", ".", "::", "and", "or")
    def bin_op_(fn, ast: AST):
        if ast.type in [".", "::"]:
            operator = ast.type
        else:
            operator = f" {ast.type} "
        return [*fn.apply(ast.first()), operator, *fn.apply(ast.second())]

    @Visitor.for_ast_types("call")
    def call_(fn, ast: AST):
        return [*fn.apply(ast.first()), "(", *fn.apply(ast.second()), ")"]

    @Visitor.for_ast_types("is_call")
    def is_call_(fn, ast: AST):
        name = ast.first().first().value[3:]
        return [*fn.apply(ast.second()), " is ", name]

    # TODO: need to work with elseif
    @Visitor.for_ast_types("if")
    def if_(fn, ast: AST):
        return ["if ", *fn.apply(ast.first())]

    @Visitor.for_ast_types("return")
    def return_(fn, ast: AST):
        return ["return"]
