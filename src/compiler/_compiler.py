from __future__ import annotations
from seer._seer import Seer
from error import Raise
from ast import AstNode, AST
from llvmlite import ir

from compiler._ir_generation import IRGenerationProcedure
from compiler._context import Context, Scope
from compiler._object import Object
from compiler._options import Options
from compiler._exceptions import Exceptions
from compiler._definitions import Definitions
from compiler._ir_types import IrTypes

class Compiler():
    _build_map = {}
    _ir_generation_procedures = []
    _is_init = False

    @classmethod
    def run(cls, ast : AST, txt : str, visitors):
        callback = Compiler.Callback(txt=txt)
        options = Options(should_not_emit_ir=True, visitors=visitors)
        module = ir.Module()
        global_context = Compiler._generate_new_global_context(module)
        Compiler._recursive_descent_for_validation(ast.head, global_context, callback, options)

        if(callback.encountered_fatal_exception()):
            print(Exceptions.delineator, end="")
            msg = (
                "Error: One or more fatal exception were encountered",
                "during \ncompilation. \n\nFix the above errors before re-running your code.\n")
            print(*msg)
            exit(1)

        callback = Compiler.Callback(txt=txt)
        options = Options(should_not_emit_ir=False, visitors=visitors)
        module = ir.Module()
        global_context = Compiler._generate_new_global_context(module)
        Compiler._recursive_descent(ast.head, global_context, callback, options)

        return str(module)


    ################################################################################################
    ##
    ## Initialization
    ##
    ################################################################################################
    @classmethod
    def _generate_new_global_context(cls, module) -> Context:
        return Context(module, None, cls._generate_new_global_scope(module))


    @classmethod
    def _generate_new_global_scope(cls, module) -> Scope:
        global_scope = Scope(parent_scope=None)
        Compiler._init_primitive_types(global_scope)
        Compiler._init_special_objs(global_scope, module)

        return global_scope


    @classmethod
    def _init_primitive_types(cls, global_scope : Scope):
        global_scope.add_type(Seer.Types.Primitives.Int, IrTypes.int)
        global_scope.add_type(Seer.Types.Primitives.String, None)# TODO: fix
        global_scope.add_type(Seer.Types.Primitives.Float, IrTypes.float)
        global_scope.add_type(Seer.Types.Primitives.Bool,IrTypes.bool)


    @classmethod
    def _init_special_objs(cls, global_scope : Scope, module):
        ir_print_function_type =  ir.FunctionType(ir.IntType(32), [], var_arg=True)
        ir_print_function = ir.Function(
            module, 
            ir_print_function_type, 
            name="printf")
        
        global_scope.add_type(Definitions.print_function_type, ir_print_function_type)
        global_scope.add_obj(
            Definitions.print_function_name,
            Object(
                ir_print_function, 
                Definitions.print_function_type, 
                Definitions.print_function_name))


    ################################################################################################
    ##
    ## Core logic
    ##
    ################################################################################################
    @classmethod
    def get_build_procedure(cls, op : str, visitors):
        found_proc = visitors.build_map.get(op, None)
        if found_proc is None:
            print("here")
            Raise.code_error(f"op {op} is not defined in the build map")

        return found_proc


    @classmethod
    def _recursive_descent_for_validation(self,
            astnode : AstNode,
            cx : Context,
            callback : Callback,
            options : Options) -> None:

        build_procedure : IRGenerationProcedure = \
            Compiler.get_build_procedure(astnode.op, options.visitors)

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
        if any(map(lambda obj: isinstance(obj, Exceptions.AbstractException), new_objs)):
            amended_objs = []
            for obj in new_objs:
                if isinstance(obj, Exceptions.AbstractException):
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
            cx : Context, 
            callback : Compiler.Callback,
            options : Options) -> None:

        # start
        build_procedure : IRGenerationProcedure = \
            Compiler.get_build_procedure(astnode.op, options.visitors)
            
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

        def _print_exception(self, exception : Exceptions.AbstractException):
            print(exception.to_str_with_context(self.txt))
