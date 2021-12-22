from __future__ import annotations

import compiler 
from seer._utils import _deref_ir_obj_if_needed
from ast import AstNode
from llvmlite import ir

class if_statement_(compiler.IRGenerationProcedure):
    matches = ["if_statement"]

    @classmethod
    def validate_precompile(cls, 
            node : AstNode, 
            cx : compiler.Context,
            options : compiler.Options=None
            ) -> compiler.RecursiveDescentIntermediateState:

        rdstate = compiler.RecursiveDescentIntermediateState()
        # don't need to worry about new blocks
        new_contexts = [cx]

        # first child is an if-statement clause which lives in the original block
        rdstate.add_child(cx, node.vals[0])

        for child in node.vals[1:]:
            new_cx = compiler.Context(cx.module, None, compiler.Scope(parent_scope=cx.scope))
            rdstate.add_child(new_cx, child)

        return rdstate


    @classmethod
    def precompile(cls, 
            node : AstNode, 
            cx : compiler.Context,
            options : compiler.Options=None
            ) -> compiler.RecursiveDescentIntermediateState:

        rdstate = compiler.RecursiveDescentIntermediateState()
        new_blocks = [cx.builder.block]
        new_contexts = [cx]

        # first child is an if-statement clause which lives in the original block
        rdstate.add_child(cx, node.vals[0])

        for child in node.vals[1:]:
            new_block = cx.builder.append_basic_block()
            new_blocks.append(new_block)

            new_cx = compiler.Context(
                cx.module, 
                ir.IRBuilder(block=new_block),
                compiler.Scope(parent_scope=cx.scope))

            new_contexts.append(new_cx)
            rdstate.add_child(new_cx, child)

        new_blocks.append(cx.builder.append_basic_block())

        rdstate.add_arg("blocks", new_blocks)
        rdstate.add_arg("contexts", new_contexts)

        return rdstate

    
    @classmethod
    def compile(cls, 
            node : AstNode, 
            cx : compiler.Context, 
            args : dict, 
            options : compiler.Options = None) -> list[compiler.Object]:

            return []

    @classmethod
    def compile(cls, 
            node : AstNode, 
            cx : compiler.Context, 
            args : dict, 
            options : compiler.Options = None) -> list[compiler.Object]:

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

            if codeblock_cx.builder.block.is_terminated:
                i += 1
                continue

            # last block is the block added after the if complex
            codeblock_cx.builder.branch(blocks[-1])
            i += 2

        cx.builder.position_at_start(blocks[-1])

        return []
        