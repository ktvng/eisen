from __future__ import annotations

from compiler._ir_generation import IRGenerationProcedure
from compiler._context import Context
from compiler._object import Object, Stub
from compiler._options import Options
from compiler._exceptions import Exceptions

from compiler._utils import _deref_ir_obj_if_needed

from ast import AstNode

from llvmlite import ir

# TODO: fix
class function_call_(IRGenerationProcedure):
    matches = ["function_call"]

    @classmethod
    def _get_function_cobj(cls, node : AstNode) -> Object:
        return node.vals[0].compile_data[0]

    @classmethod
    def _get_function_param_cobjs(cls, node : AstNode) -> list[Object]:
        return node.vals[1].compile_data

    @classmethod
    def _get_function_returned_cobj_types(cls, func_cobj : Object) -> list[str]:
        return ["TODO"]

    @classmethod
    def validate_compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict,
            options : Options=None) -> list[Object]:

        func_cobj = cls._get_function_cobj(node)
        param_cobjs = cls._get_function_param_cobjs(node)

        return_objs = []
        for cobj in param_cobjs:
            if not cobj.is_initialized:
                exception = Exceptions.UseBeforeInitialize(
                    f"variable '{cobj.name}' used here but not initialized",
                    node.line_number)

                return_objs.append(exception)

        # TODO: enable functions that return stuff
        for return_type_str in cls._get_function_returned_cobj_types(func_cobj):
            return_objs.append(Stub(return_type_str))

        return return_objs
                

    @classmethod
    def compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict, 
            options : Options = None) -> list[Object]:

        func_cobj = cls._get_function_cobj(node)
        param_cobjs = cls._get_function_param_cobjs(node)

        ir_param_objs = [_deref_ir_obj_if_needed(cobj, cx) for cobj in param_cobjs]

        # TODO: fix return value
        return [Object(
            cx.builder.call(func_cobj.get_ir(), ir_param_objs),
            "TODO")]

