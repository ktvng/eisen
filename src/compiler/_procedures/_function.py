from __future__ import annotations

from compiler._ir_generation import IRGenerationProcedure, RecursiveDescentIntermediateState
from compiler._context import Context, Scope
from compiler._object import Object, Stub
from compiler._options import Options
from compiler._exceptions import Exceptions

from astnode import AstNode

from llvmlite import ir

# TODO: fix
class function_(IRGenerationProcedure):
    matches = ["function"]

    @classmethod
    def _get_function_decl_names_and_types_in_tuple_form(cls, node : AstNode):
        # params/returns is a tuple of ':' operation nodes. we need to get the leaf_val
        # from the left and right children of each node in params
        params = node.vals[1].vals
        if params and params[0].op == "var_decl_tuple":
            params = params[0].vals

        param_tuples = [(p.vals[0].leaf_val, p.vals[1].leaf_val) for p in params]

        # if no return node is provided
        return_tuples = []

        # if a return node is provided
        if len(node.vals) == 4:
            returns = node.vals[2].vals
            return_tuples = [(r.val[0].leaf_val, r.vals[1].leaf_val) for r in returns]


        return param_tuples, return_tuples

    @classmethod
    def _get_function_type(cls, node : AstNode, cx : Context):
        param_tuples, return_tuples = \
            cls._get_function_decl_names_and_types_in_tuple_form(node)
        
        param_types = [x[1] for x in param_tuples]
        return_types = [x[1] for x in return_tuples]

        function_ir_types = []
        function_ir_types += [cx.scope.get_ir_type(type) for type in param_types]
        function_ir_types += [cx.scope.get_ir_type(type) for type in return_types]

        ir_type = ir.FunctionType(ir.VoidType(), function_ir_types)

        return f"({','.join(param_types)}) -> ({','.join(return_types)})", ir_type

    @classmethod
    def _get_function_name(cls, node : AstNode):
        return node.vals[0].leaf_val

    @classmethod
    def _add_parameters_to_new_context(cls, node : AstNode, cx : Context, func):
        param_tuples, return_tuples = \
            cls._get_function_decl_names_and_types_in_tuple_form(node)

        for i, param_tuple in enumerate(param_tuples):
            name, type = param_tuple
            ir_obj = cx.builder.alloca(cx.scope.get_ir_type(type), name=name)
            compiler_obj = Object(
                ir_obj,
                type,
                name=name)
            cx.scope.add_obj(name, compiler_obj)
            cx.builder.store(func.args[i], ir_obj)

        for name, type in return_tuples:
            cx.builder.alloca(cx.scope.get_ir_type(type), name=name)
            compiler_obj = Object(
                ir_obj,
                type,
                name=name)
            cx.scope.add_obj(name, compiler_obj)


    @classmethod
    def validate_precompile(cls, 
            node : AstNode,
            cx : Context, 
            options : Options = None
            ) -> RecursiveDescentIntermediateState:

        func_name = cls._get_function_name(node)
        func_type, ir_type = cls._get_function_type(node, cx)

        func_obj = Stub(func_type, name=func_name)
        cx.scope.add_obj(func_name, func_obj)

        func_context = Context(cx.module, None, Scope(parent_scope=cx.scope))
        param_tuples, return_tuples = cls._get_function_decl_names_and_types_in_tuple_form(node)
        for param_tuple in param_tuples:
            name, type = param_tuple
            func_context.scope.add_obj(name, Stub(type, name=name))

        rdstate = RecursiveDescentIntermediateState()
        rdstate.add_arg("function", func_obj)
        rdstate.add_child(func_context, node.vals[-1])

        return rdstate


    @classmethod
    def precompile(cls, 
            node : AstNode, 
            cx : Context,
            options : Options=None
            ) -> RecursiveDescentIntermediateState:

        # TODO: impl
        func_name = cls._get_function_name(node)
        func_type, ir_type = cls._get_function_type(node, cx)
        # TODO: figure out how to get parameter names
        func = ir.Function(cx.module, ir_type, name=func_name)

        compiler_obj = Object(
            func,
            func_type,
            name=func_name)

        cx.scope.add_obj(func_name, compiler_obj)

        builder = ir.IRBuilder(func.append_basic_block("entry"))
        new_context = Context(
            cx.module, 
            builder, 
            Scope(parent_scope=cx.scope))

        cls._add_parameters_to_new_context(node, new_context, func)

        rdstate = RecursiveDescentIntermediateState()
        rdstate.add_arg("function", compiler_obj)
        rdstate.add_arg("new_cx", new_context)
        rdstate.add_child(new_context, node.vals[-1])

        return rdstate

    @classmethod
    def validate_compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict,
            options : Options=None) -> list[Object]:

        return [args["function"]]

    @classmethod
    def compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict, 
            options : Options = None) -> list[Object]:

        new_cx = args["new_cx"]
        if(not new_cx.builder.block.is_terminated):
            new_cx.builder.ret_void()

        return [args["function"]]


class return_(IRGenerationProcedure):
    matches = ["return"]

    @classmethod
    def validate_compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict,
            options : Options=None) -> list[Object]:

        return []

    @classmethod
    def compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict, 
            options : Options = None) -> list[Object]:
        
        cx.builder.ret_void()
        return []

