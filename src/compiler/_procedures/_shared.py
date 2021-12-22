from __future__ import annotations

from compiler._ir_generation import IRGenerationProcedure
from compiler._context import Context
from compiler._object import Object
from compiler._options import Options

from ast import AstNode

from llvmlite import ir

class default_(IRGenerationProcedure):
    matches = ["start", "params_decl", "codeblock"]

class unwrap_(IRGenerationProcedure):
    matches = ["params", "vars", "tuple", "var_decl_tuple", "var_name_tuple"]

    @classmethod
    def validate_compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict,
            options : Options=None) -> list[Object]:

        return cls.compile(node, cx, args, options)

    @classmethod
    def compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict, 
            options : Options = None) -> list[Object]:

        return [child.compile_data[0] for child in node.vals]

    