from __future__ import annotations
from os import removedirs
from typing import ContextManager, List, Tuple
from seer import Seer
from error import Raise
from astnode import AstNode
from llvmlite import ir

class Compiler():
    from ._definitions import Definitions
    from ._ir_types import IrTypes
    from ._exceptions import Exceptions
    from ._object import Object, Stub
    from ._context import Scope, Context
    from ._options import Options
    from ._ir_generation import IRGenerationProcedure, RecursiveDescentIntermediateState

    _build_map = {}
    _ir_generation_procedures = []
    _is_init = False

    @classmethod
    def run(cls, asthead : AstNode, txt : str):
        Compiler._init_class()

        callback = Compiler.Callback(txt=txt)
        options = Compiler.Options(should_not_emit_ir=True)
        module = ir.Module()
        global_context = Compiler._generate_new_global_context(module)
        Compiler._recursive_descent_for_validation(asthead, global_context, callback, options)

        if(callback.encountered_fatal_exception()):
            print(Compiler.Exceptions.delineator, end="")
            msg = (
                "Error: One or more fatal exception were encountered",
                "during \ncompilation. \n\nFix the above errors before re-running your code.\n")
            print(*msg)
            exit(1)

        callback = Compiler.Callback(txt=txt)
        options = Compiler.Options(should_not_emit_ir=False)
        module = ir.Module()
        global_context = Compiler._generate_new_global_context(module)
        Compiler._recursive_descent(asthead, global_context, callback, options)

        return str(module)


    ################################################################################################
    ##
    ## Initialization
    ##
    ################################################################################################
    @classmethod
    def _init_class(cls):
        if cls._is_init:
            return

        cls._is_init = True

        cls.ir_generation_procedures = [
            Compiler.default_,
            Compiler.unwrap_,
            Compiler.int_,
            Compiler.bool_,
            Compiler.string_,
            Compiler.tag_,
            Compiler.var_decl_,
            Compiler.var_,
            Compiler.function_call_,
            Compiler.function_,
            Compiler.return_,
            Compiler.assigns_,
            Compiler.bin_op_,
            Compiler.let_,
            Compiler.if_statement_,
            Compiler.while_statement_
        ]

        cls._build_map = {}
        for proc in cls.ir_generation_procedures:
            if not proc.matches:
                Raise.code_error(f"{proc} requires matches field")
            
            for match in proc.matches:
                cls._build_map[match] = proc
    

    @classmethod
    def _generate_new_global_context(cls, module) -> Compiler.Context:
        return Compiler.Context(module, None, cls._generate_new_global_scope(module))


    @classmethod
    def _generate_new_global_scope(cls, module) -> Compiler.Scope:
        global_scope = Compiler.Scope(parent_scope=None)
        Compiler._init_primitive_types(global_scope)
        Compiler._init_special_objs(global_scope, module)

        return global_scope


    @classmethod
    def _init_primitive_types(cls, global_scope : Compiler.Scope):
        global_scope.add_type(Seer.Types.Primitives.Int, Compiler.IrTypes.int)
        global_scope.add_type(Seer.Types.Primitives.String, None)# TODO: fix
        global_scope.add_type(Seer.Types.Primitives.Float, Compiler.IrTypes.float)
        global_scope.add_type(Seer.Types.Primitives.Bool, Compiler.IrTypes.bool)


    @classmethod
    def _init_special_objs(cls, global_scope : Compiler.Scope, module):
        ir_print_function_type =  ir.FunctionType(ir.IntType(32), [], var_arg=True)
        ir_print_function = ir.Function(
            module, 
            ir_print_function_type, 
            name="printf")
        
        global_scope.add_type(Compiler.Definitions.print_function_type, ir_print_function_type)
        global_scope.add_obj(
            Compiler.Definitions.print_function_name,
            Compiler.Object(
                ir_print_function, 
                Compiler.Definitions.print_function_type, 
                Compiler.Definitions.print_function_name))


    ################################################################################################
    ##
    ## Core logic
    ##
    ################################################################################################
    @classmethod
    def get_build_procedure(cls, op : str):
        found_proc = cls._build_map.get(op, None)
        if found_proc is None:
            Raise.code_error(f"op {op} is not defined in the build map")
        
        return found_proc


    @classmethod
    def _recursive_descent_for_validation(self,
            astnode : AstNode,
            cx : Compiler.Context,
            callback : Compiler.Callback,
            options : Compiler.Options) -> None:

        build_procedure : Compiler.IRGenerationProcedure = Compiler.get_build_procedure(astnode.op)
        rdstate = build_procedure.validate_precompile(astnode, cx, options)

        for child_path in rdstate.get_paths():
            child_cx, child_node = child_path
            self._recursive_descent_for_validation(child_node, child_cx, callback, options)

        new_objs = build_procedure.validate_compile(astnode, cx, rdstate.args, options)
        
        # @typecheck
        if not isinstance(new_objs, list):
            Raise.code_error(f"new_objs is not instance of list, got {type(new_objs)} from {build_procedure}")

        # NOTE:
        # The list of new_objs is expected to contain exceptions and objects together. If exceptions 
        # contain references to stub objects, these are unpacked into the amended objs. Otherwise 
        # the exceptions are filtered out. All objects are moved to amended_objs in order
        if any(map(lambda obj: isinstance(obj, Compiler.Exceptions.AbstractException), new_objs)):
            amended_objs = []
            for obj in new_objs:
                if isinstance(obj, Compiler.Exceptions.AbstractException):
                    callback._print_exception(obj)
                    callback.notify_of_fatal_exception()
                    if(obj.has_stub()):
                        amended_objs.append(obj.get_stub())
                else:
                    amended_objs.append(obj)
            
            new_objs = amended_objs

        astnode.compile_data = new_objs 


    @classmethod
    def _recursive_descent(self, 
            astnode : AstNode, 
            cx : Compiler.Context, 
            callback : Compiler.Callback,
            options : Compiler.Options) -> None:

        # start
        build_procedure : Compiler.IRGenerationProcedure = Compiler.get_build_procedure(astnode.op)
        rdstate = build_procedure.precompile(astnode, cx, options)

        for child_path in rdstate.get_paths():
            child_cx, child_node = child_path
            self._recursive_descent(child_node, child_cx, callback, options)

        new_objs = build_procedure.compile(astnode, cx, rdstate.args, options)
        
        # @typecheck
        if not isinstance(new_objs, list):
            Raise.code_error(f"new_objs is not instance of list, got {type(new_objs)} from {build_procedure}")

        astnode.compile_data = new_objs
     

    @classmethod
    def _get_children_compiler_objects(cls, node : AstNode):
        return [child.compile_data for child in node.vals]
    


    ################################################################################################
    ##
    ## Callback
    ##
    ################################################################################################

    class Callback():
        def __init__(self, txt : str):
            self.txt = txt
            self._encountered_fatal_exception = False

        def notify_of_fatal_exception(self):
            self._encountered_fatal_exception = True

        def encountered_fatal_exception(self):
            return self._encountered_fatal_exception

        def _print_exception(self, exception : Compiler.Exceptions.AbstractException):
            print(exception.to_str_with_context(self.txt))


    ################################################################################################
    ##
    ## Compiler generation procedures
    ##
    ################################################################################################
    from ._procedures._basic import string_, int_, bool_, tag_, var_
    from ._procedures._shared import default_, unwrap_
    from ._procedures._var_decl import var_decl_, let_
    from ._procedures._function_call import function_call_
    from ._procedures._function import function_, return_
    from ._procedures._assigns import assigns_
    from ._procedures._bin_op import bin_op_
    from ._procedures._if_statement import if_statement_
    from ._procedures._while_statement import while_statement_