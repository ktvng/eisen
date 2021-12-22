from __future__ import annotations

import compiler

from compiler._utils import _deref_ir_obj_if_needed

from ast import AstNode

from llvmlite import ir

# TODO: fix
class function_call_(compiler.IRGenerationProcedure):
    matches = ["function_call"]

    @classmethod
    def _get_function_cobj(cls, node : AstNode) -> compiler.Object:
        return node.vals[0].compile_data[0]

    @classmethod
    def _get_function_param_cobjs(cls, node : AstNode) -> list[compiler.Object]:
        return node.vals[1].compile_data

    @classmethod
    def _get_function_returned_cobj_types(cls, func_cobj : compiler.Object) -> list[str]:
        return ["TODO"]

    @classmethod
    def validate_compile(cls, 
            node : AstNode, 
            cx : compiler.Context, 
            args : dict,
            options : compiler.Options=None) -> list[compiler.Object]:

        func_cobj = cls._get_function_cobj(node)
        param_cobjs = cls._get_function_param_cobjs(node)

        return_objs = []
        for cobj in param_cobjs:
            if not cobj.is_initialized:
                exception = compiler.Exceptions.UseBeforeInitialize(
                    f"variable '{cobj.name}' used here but not initialized",
                    node.line_number)

                return_objs.append(exception)

        # TODO: enable functions that return stuff
        for return_type_str in cls._get_function_returned_cobj_types(func_cobj):
            return_objs.append(compiler.Stub(return_type_str))

        return return_objs
                

    @classmethod
    def compile(cls, 
            node : AstNode, 
            cx : compiler.Context, 
            args : dict, 
            options : compiler.Options = None) -> list[compiler.Object]:

        func_cobj = cls._get_function_cobj(node)
        param_cobjs = cls._get_function_param_cobjs(node)

        ir_param_objs = [_deref_ir_obj_if_needed(cobj, cx) for cobj in param_cobjs]

        # TODO: fix return value
        return [compiler.Object(
            cx.builder.call(func_cobj.get_ir(), ir_param_objs),
            "TODO")]
