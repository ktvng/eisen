from __future__ import annotations

from compiler._ir_generation import IRGenerationProcedure, RecursiveDescentIntermediateState
from compiler._context import Context, Scope
from compiler._object import Object
from compiler._options import Options
from compiler._exceptions import Exceptions

from compiler._utils import _deref_ir_obj_if_needed

from astnode import AstNode

from llvmlite import ir

class if_statement_(IRGenerationProcedure):
    matches = ["if_statement"]

    @classmethod
    def validate_precompile(cls, 
            node : AstNode, 
            cx : Context,
            options : Options=None
            ) -> RecursiveDescentIntermediateState:

        rdstate = RecursiveDescentIntermediateState()
        # don't need to worry about new blocks
        new_contexts = [cx]

        # first child is an if-statement clause which lives in the original block
        rdstate.add_child(cx, node.vals[0])

        for child in node.vals[1:]:
            new_cx = Context(cx.module, None, Scope(parent_scope=cx.scope))
            rdstate.add_child(new_cx, child)

        return rdstate


    @classmethod
    def precompile(cls, 
            node : AstNode, 
            cx : Context,
            options : Options=None
            ) -> RecursiveDescentIntermediateState:

        rdstate = RecursiveDescentIntermediateState()
        new_blocks = [cx.builder.block]
        new_contexts = [cx]

        # first child is an if-statement clause which lives in the original block
        rdstate.add_child(cx, node.vals[0])

        for child in node.vals[1:]:
            new_block = cx.builder.append_basic_block()
            new_blocks.append(new_block)

            new_cx = Context(
                cx.module, 
                ir.IRBuilder(block=new_block),
                Scope(parent_scope=cx.scope))

            new_contexts.append(new_cx)
            rdstate.add_child(new_cx, child)

        new_blocks.append(cx.builder.append_basic_block())

        rdstate.add_arg("blocks", new_blocks)
        rdstate.add_arg("contexts", new_contexts)

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

        n = len(node.vals)
        blocks = args["blocks"]
        contexts = args["contexts"]

        i = 0
        while i + 1 < n:
            statement_cx = contexts[i]
            codeblock_block = blocks[i+1]
            next_statement_block = blocks[i+2]

            statement_compiler_obj = node.vals[i].compile_data[0]

            statement_cx.builder.cbranch(
                _deref_ir_obj_if_needed(statement_compiler_obj, cx),
                codeblock_block,
                next_statement_block)

            i += 2

        # handle the case of hanging 'else' statement
        if n % 2 == 1:
            else_cx = contexts[-1]
            else_cx.builder.branch(blocks[-1])

        # connect all codeblock_blocks to the final codeblock
        i = 1
        while i < n:
            codeblock_cx = contexts[i]

            # last block is the block added after the if complex
            codeblock_cx.builder.branch(blocks[-1])
            i += 2

        cx.builder.position_at_start(blocks[-1])

        return []