from __future__ import annotations

import alpaca.compiler as compiler
from alpaca.asts import ASTNode
from llvmlite import ir

# children are: name params return codeblock
class function_(compiler.IRGenerationProcedure):
    matches = ["function"]

    @classmethod
    def _get_function_decl_names_and_types_in_tuple_form(cls, node : ASTNode):
        # params/returns is a tuple of ':' operation nodes. we need to get the leaf_val
        # from the left and right children of each node in params
        params = node.children[1].children
        if params and params[0].match_with() == "var_decl_tuple":
            params = params[0].children

        param_tuples = [(p.children[0].value, p.children[1].value) for p in params]

        # if no return node is provided
        return_tuples = []

        # if a return node is provided
        if len(node.children) == 4:
            return_decl_node = node.children[2]
            params_node = return_decl_node.children[1] # first node is '->

            if params_node.match_with() == "params_decl":
                var_decl_nodes = params_node.children[0].children # node is var_decl_tuple
            else:
                var_decl_nodes = [params_node]
            return_tuples = [(r.children[0].value, r.children[1].value) for r in var_decl_nodes]

        return param_tuples, return_tuples

    @classmethod
    def _get_function_type(cls, node : ASTNode, cx : compiler.Context):
        param_tuples, return_tuples = \
            cls._get_function_decl_names_and_types_in_tuple_form(node)
        
        param_types = [x[1] for x in param_tuples]
        return_types = [x[1] for x in return_tuples]

        function_ir_types = [] \
            + [cx.scope.get_ir_type(type) for type in param_types] \
            + [cx.scope.get_ir_type(type).as_pointer() for type in return_types]

        ir_type = ir.FunctionType(ir.VoidType(), function_ir_types)

        return f"({','.join(param_types)}) -> ({','.join(return_types)})", ir_type

    @classmethod
    def _get_function_name(cls, node : ASTNode):
        return node.children[0].value

    @classmethod
    def _add_parameters_to_new_context(cls, node : ASTNode, cx : compiler.Context, func):
        param_tuples, return_tuples = \
            cls._get_function_decl_names_and_types_in_tuple_form(node)

        for i, param_tuple in enumerate(param_tuples):
            name, type = param_tuple
            ir_obj = cx.builder.alloca(cx.scope.get_ir_type(type), name=name)
            compiler_obj = compiler.Object(
                ir_obj,
                type,
                name=name)
            cx.scope.add_obj(name, compiler_obj)
            cx.builder.store(func.args[i], ir_obj)

        for i, return_tuple in enumerate(return_tuples):
            name, type = return_tuple
            ir_tmp = cx.builder.alloca(cx.scope.get_ir_type(type).as_pointer())
            cx.builder.store(func.args[i + len(param_tuples)], ir_tmp)
            ir_obj = cx.builder.load(ir_tmp, name=name)

            compiler_obj = compiler.Object(
                ir_obj,
                type,
                name=name)
            cx.scope.add_obj(name, compiler_obj)


    @classmethod
    def validate_precompile(cls, 
            node : ASTNode,
            cx : compiler.Context, 
            options : compiler.Options = None
            ) -> compiler.RecursiveDescentIntermediateState:

        func_name = cls._get_function_name(node)
        func_type, ir_type = cls._get_function_type(node, cx)

        func_obj = compiler.Stub(func_type, name=func_name)
        cx.scope.add_obj(func_name, func_obj)

        func_context = compiler.Context(cx.module, None, compiler.Scope(parent_scope=cx.scope))
        param_tuples, return_tuples = cls._get_function_decl_names_and_types_in_tuple_form(node)
        for param_tuple in param_tuples:
            name, type = param_tuple
            func_context.scope.add_obj(name, compiler.Stub(type, name=name))

        for return_tuple in return_tuples:
            name, type = return_tuple
            func_context.scope.add_obj(name, compiler.Stub(type, name=name))

        rdstate = compiler.RecursiveDescentIntermediateState()
        rdstate.add_arg("function", func_obj)
        rdstate.add_child(func_context, node.children[-1])

        return rdstate


    @classmethod
    def precompile(cls, 
            node : ASTNode, 
            cx : compiler.Context,
            options : compiler.Options=None
            ) -> compiler.RecursiveDescentIntermediateState:

        func_name = cls._get_function_name(node)
        func_type, ir_type = cls._get_function_type(node, cx)
        func = ir.Function(cx.module, ir_type, name=func_name)

        compiler_obj = compiler.Object(
            func,
            func_type,
            name=func_name)

        cx.scope.add_obj(func_name, compiler_obj)

        builder = ir.IRBuilder(func.append_basic_block("entry"))
        new_context = compiler.Context(
            cx.module, 
            builder, 
            compiler.Scope(parent_scope=cx.scope))

        cls._add_parameters_to_new_context(node, new_context, func)

        rdstate = compiler.RecursiveDescentIntermediateState()
        rdstate.add_arg("function", compiler_obj)
        rdstate.add_arg("new_cx", new_context)
        rdstate.add_child(new_context, node.children[-1])

        return rdstate

    @classmethod
    def validate_compile(cls, 
            node : ASTNode, 
            cx : compiler.Context, 
            args : dict,
            options : compiler.Options=None) -> list[compiler.Object]:

        return [args["function"]]

    @classmethod
    def compile(cls, 
            node : ASTNode, 
            cx : compiler.Context, 
            args : dict, 
            options : compiler.Options = None) -> list[compiler.Object]:

        new_cx = args["new_cx"]
        if(not new_cx.builder.block.is_terminated):
            new_cx.builder.ret_void()

        return [args["function"]]






class return_(compiler.IRGenerationProcedure):
    matches = ["RETURN"]

    @classmethod
    def compile(cls, 
            node : ASTNode, 
            cx : compiler.Context, 
            args : dict, 
            options : compiler.Options = None) -> list[compiler.Object]:
        
        cx.builder.ret_void()
        return []
