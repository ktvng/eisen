from __future__ import annotations

import compiler
from ast import AstNode

class default_(compiler.IRGenerationProcedure):
    matches = ["start", "params_decl", "codeblock"]

class unwrap_(compiler.IRGenerationProcedure):
    matches = ["params", "vars", "tuple", "var_decl_tuple", "var_name_tuple"]

    @classmethod
    def validate_compile(cls, 
            node : AstNode, 
            cx : compiler.Context, 
            args : dict,
            options : compiler.Options=None) -> list[compiler.Object]:

        return cls.compile(node, cx, args, options)

    @classmethod
    def compile(cls, 
            node : AstNode, 
            cx : compiler.Context, 
            args : dict, 
            options : compiler.Options = None) -> list[compiler.Object]:

        return [child.compile_data[0] for child in node.vals]

    