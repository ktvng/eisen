from __future__ import annotations

from compiler._ir_generation import IRGenerationProcedure, RecursiveDescentIntermediateState
from compiler._context import Context, Scope
from compiler._object import Object
from compiler._options import Options
from compiler._exceptions import Exceptions

from compiler._utils import _deref_ir_obj_if_needed

from astnode import AstNode

from llvmlite import ir

class while_statement_(IRGenerationProcedure):
    matches = ["while_statement"]

    @classmethod
    def validate_precompile(cls, 
            node : AstNode, 
            cx : Context,
            options : Options=None
            ) -> RecursiveDescentIntermediateState:

        rdstate = RecursiveDescentIntermediateState()
        statement_cx = Context(cx.module, None, Scope(parent_scope=cx.scope))
        rdstate.add_child(statement_cx, node.vals[0])                

        body_cx = Context(cx.module, None, Scope(parent_scope=cx.scope))
        rdstate.add_child(body_cx, node.vals[1])

        return rdstate


    @classmethod
    def precompile(cls, 
            node : AstNode, 
            cx : Context,
            options : Options=None
            ) -> RecursiveDescentIntermediateState:

        rdstate = RecursiveDescentIntermediateState()

        statement_block = cx.builder.append_basic_block()
        statement_cx = Context(
            cx.module,
            ir.IRBuilder(block=statement_block),
            Scope(parent_scope=cx.scope))

        body_block = cx.builder.append_basic_block()
        body_cx = Context(
            cx.module,
            ir.IRBuilder(block=body_block),
            Scope(parent_scope=cx.scope))

        after_block = cx.builder.append_basic_block()

        rdstate.add_child(statement_cx, node.vals[0])
        rdstate.add_child(body_cx, node.vals[1])

        rdstate.add_arg("statement_block", statement_block)
        rdstate.add_arg("statement_cx", statement_cx)
        rdstate.add_arg("body_block", body_block)
        rdstate.add_arg("body_cx", body_cx)
        rdstate.add_arg("after_block", after_block)

        return rdstate


    @classmethod
    def compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict, 
            options : Options = None) -> list[Object]:

        return []


    @classmethod
    def compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict, 
            options : Options = None) -> list[Object]:

        statement_block = args["statement_block"]
        statement_cx = args["statement_cx"]
        body_block = args["body_block"]
        body_cx = args["body_cx"]
        after_block = args["after_block"]

        statement_compiler_obj = node.vals[0].compile_data[0]
        statement_cx.builder.cbranch(
                _deref_ir_obj_if_needed(statement_compiler_obj, cx),
                body_block,
                after_block)

        body_cx.builder.branch(statement_block)
        cx.builder.branch(statement_block)
        cx.builder.position_at_start(after_block)

        return []
    