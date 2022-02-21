from __future__ import annotations

import alpaca
from error import Raise
from alpaca.parser import AbstractBuilder, CommonBuilder
from alpaca.compiler import AbstractVisitor
from alpaca.asts import ASTNode
from alpaca import compiler

class Builder(AbstractBuilder):
    build_map = {}

    @AbstractBuilder.build_procedure(build_map, "filter_build")
    def filter_build_(components : list[ASTNode], *args) -> list[ASTNode]:
        newnode = CommonBuilder.build(components, *args)[0]
        filtered_children = [c for c in newnode.children if
            (c.type != "keyword" and c.type != "symbol")]

        newnode.children = filtered_children
        newnode.children = filtered_children
        return [newnode]


#####################################################
class AbstractContext():
    def __init__(self, params : dict = {}):
        self.params = params

    def add(self, key : str, val):
        self.params[key] = val

    def get(self, key : str):
        return self.params.get(key, None)

class AbstractVisitor2():
    def visit(self, astnode : ASTNode, cx : AbstractContext):
        pass






def ts(astnode : ASTNode, closure={}):
    if astnode.match_with() == "lambda":
        return f"\L {ts(astnode.children[0], closure)}.{ts(astnode.children[1], closure)}"
    elif astnode.match_with() == "TAG":
        if astnode.value in closure:
            return obj_ts(closure[astnode.value])
        return astnode.value
    elif astnode.match_with() == "apply":
        return f"({ts(astnode.children[0], closure)} {ts(astnode.children[1], closure)})"
        
def obj_ts(obj):
    if obj["type"] == "lambda":
        return f"\L {obj['binds']['name']}.{ts(obj['body'], obj['closure'])}"
    if obj["type"] == "def":
        return ts(obj["body"])
    if obj["type"] == "tag":
        return obj["name"]




def visit(astnode : ASTNode, cx : AbstractContext):
    return astnode.visitor.visit(astnode, cx)

class print_(AbstractVisitor2):
    matches = ["print"]

    def visit(self, astnode: ASTNode, cx: AbstractContext):
        obj = visit(astnode.children[0], cx)
        print(obj_ts(obj))
        return obj

class start_(AbstractVisitor2):
    matches = ["start"]

    def visit(self, astnode: ASTNode, cx: AbstractContext):
        results = [visit(child, cx) for child in astnode.children]
        return results

class lambda_(AbstractVisitor2):
    matches = ["lambda"]

    def visit(self, astnode: ASTNode, cx: AbstractContext):
        name = visit(astnode.children[0], cx)
        return {
            "type": "lambda", 
            "closure": { **cx.params["scope"] }, 
            "binds": name, 
            "body": astnode.children[1]}

class tag_(AbstractVisitor2):
    matches = ["TAG"]
    
    def visit(self, astnode: ASTNode, cx: AbstractContext):
        found_value = cx.params["scope"].get(astnode.value, None)
        if found_value is not None:
            return found_value

        return {
            "type": "tag", 
            "name": astnode.value}
    
class def_(AbstractVisitor2):
    matches = ["def"]

    def visit(self, astnode: ASTNode, cx: AbstractContext):
        name = visit(astnode.children[0], cx)["name"]
        obj = {
            "type": "def",
            "body": astnode.children[1]}
        cx.params["scope"][name] = obj
        return obj
    
class apply_(AbstractVisitor2):
    matches = ['apply']

    def visit(self, astnode: ASTNode, cx: AbstractContext):
        fn = visit(astnode.children[0], cx)
        arg = visit(astnode.children[1], cx)

        if arg["type"] == "def":
            arg = visit(arg["body"], cx)
        if fn["type"] == "def":
            fn = visit(fn["body"], cx)

        if fn["type"] != "lambda":
            Raise.error("apply expects function as first argument")

        bound_tag = fn["binds"]["name"]
        fn["closure"][bound_tag] = arg
        new_scope = { **cx.params["scope"], **fn["closure"] }
        new_cx = AbstractContext({ "scope": new_scope })

        return visit(fn["body"], new_cx)

#####################################################
class LambRunner():
    def __init__(self):
        self.build_map = {}

    visitors = [
        start_,
        lambda_,
        tag_,
        apply_,
        def_,
        print_,
    ]

    def run(self, ast : alpaca.asts.AST):
        self._create_build_map()
        self._add_visitors(ast.head)
        global_context = AbstractContext({"scope": {}})
        return visit(ast.head, global_context)

    def _create_build_map(self):
        for visitor in self.visitors:
            for match in visitor.matches:
                self.build_map[match] = visitor

    def _add_visitors(self, astnode : ASTNode):
        visitor = self.build_map.get(astnode.match_with(), None)
        if visitor is None:
            Raise.error(f"cannot find visitor matching {astnode.match_with()}")

        astnode.visitor = visitor()
        for child in astnode.children:
            self._add_visitors(child)

        