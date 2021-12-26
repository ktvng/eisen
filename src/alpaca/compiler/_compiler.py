from __future__ import annotations
from error import Raise
from alpaca.asts import ASTNode, AST
from llvmlite import ir

from alpaca.compiler._ir_generation import IRGenerationProcedure
from alpaca.compiler._context import Context
from alpaca.compiler._options import Options
from alpaca.compiler._exceptions import Exceptions
from alpaca.compiler._abstractvisitor import AbstractVisitor

def run(ast : AST, txt : str, visitor : AbstractVisitor) -> str:
    return Compiler.run(ast, txt, visitor)

class Compiler():
    @classmethod
    def run(cls, ast : AST, txt : str, visitor : AbstractVisitor) -> str:
        if not ast or ast is None:
            return ""

        visitor.init(txt)
        options = Options(should_not_emit_ir=True)
        module = ir.Module()
        global_context = visitor.new_global_context(module)
        Compiler._recursive_descent_for_validation(ast.head, global_context, visitor, options)

        visitor.finally_handle_exceptions()

        options = Options(should_not_emit_ir=False)
        module = ir.Module()
        global_context = visitor.new_global_context(module)
        Compiler._recursive_descent(ast.head, global_context, visitor, options)

        return str(module)


    ################################################################################################
    ##
    ## Core logic
    ##
    ################################################################################################
    @classmethod
    def get_build_procedure(cls, op : str, visitor):
        found_proc = visitor.build_map.get(op, None)
        if found_proc is None:
            Raise.code_error(f"op {op} is not defined in the build map")

        return found_proc


    @classmethod
    def _recursive_descent_for_validation(self,
            astnode : ASTNode,
            cx : Context,
            visitor : AbstractVisitor,
            options : Options) -> None:

        build_procedure : IRGenerationProcedure = \
            Compiler.get_build_procedure(astnode.match_with(), visitor)

        rdstate = build_procedure.validate_precompile(astnode, cx, options)

        for child_path in rdstate.get_paths():
            child_cx, child_node = child_path
            self._recursive_descent_for_validation(child_node, child_cx, visitor, options)

        new_objs = build_procedure.validate_compile(astnode, cx, rdstate.args, options)
        
        # @typecheck
        if not isinstance(new_objs, list):
            Raise.code_error(f"new_objs is not instance of list, got {type(new_objs)} from {build_procedure}")

        # NOTE:
        # The list of new_objs is expected to contain exceptions and objects together. If exceptions 
        # contain references to stub objects, these are unpacked into the amended objs. Otherwise 
        # the exceptions are filtered out. All objects are moved to amended_objs in order
        if any(map(lambda obj: isinstance(obj, Exceptions.AbstractException), new_objs)):
            amended_objs = []
            for obj in new_objs:
                if isinstance(obj, Exceptions.AbstractException):
                    visitor.exception_callback(obj)
                    if(obj.has_stub()):
                        amended_objs.append(obj.get_stub())
                else:
                    amended_objs.append(obj)
            
            new_objs = amended_objs

        astnode.compile_data = new_objs 


    @classmethod
    def _recursive_descent(self, 
            astnode : ASTNode, 
            cx : Context, 
            visitor : AbstractVisitor,
            options : Options) -> None:

        # start
        build_procedure : IRGenerationProcedure = \
            Compiler.get_build_procedure(astnode.match_with(), visitor)
            
        rdstate = build_procedure.precompile(astnode, cx, options)

        for child_path in rdstate.get_paths():
            child_cx, child_node = child_path
            self._recursive_descent(child_node, child_cx, visitor, options)

        new_objs = build_procedure.compile(astnode, cx, rdstate.args, options)
        
        # @typecheck
        if not isinstance(new_objs, list):
            Raise.code_error(f"new_objs is not instance of list, got {type(new_objs)} from {build_procedure}")

        astnode.compile_data = new_objs
