from __future__ import annotations

import alpaca.compiler as compiler
from seer._utils import _deref_ir_obj_if_needed
from alpaca.asts import ASTNode

# TODO: fix
class function_call_(compiler.IRGenerationProcedure):
    matches = ["function_call"]

    @classmethod
    def _get_function_cobj(cls, node : ASTNode) -> compiler.Object:
        return node.children[0].compile_data[0]

    @classmethod
    def _get_function_param_cobjs(cls, node : ASTNode) -> list[compiler.Object]:
        return node.children[1].compile_data

    @classmethod
    def _get_function_returned_cobj_types(cls, func_cobj : compiler.Object) -> list[str]:
        return (func_cobj.type.split('->')[1]
            .strip()[1:-1]
            .split(','))

    @classmethod
    def validate_compile(cls, 
            node : ASTNode, 
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
            node : ASTNode, 
            cx : compiler.Context, 
            args : dict, 
            options : compiler.Options = None) -> list[compiler.Object]:

        func_cobj = cls._get_function_cobj(node)
        param_cobjs = cls._get_function_param_cobjs(node)
        return_cobjs = cls._make_return_ir_objs(cx, func_cobj)

        ir_param_objs = [_deref_ir_obj_if_needed(cobj, cx) for cobj in param_cobjs] \
            + [cobj.get_ir() for cobj in return_cobjs]

        cx.builder.call(func_cobj.get_ir(), ir_param_objs)

        return return_cobjs

    @classmethod
    def _make_return_ir_objs(cls, cx : compiler.Context, func_cobj : compiler.Object):
        return_ctypes = cls._get_function_returned_cobj_types(func_cobj)

        if len(return_ctypes) == 1 and return_ctypes[0] == "void":
            return []

        def _make_ir_obj(cobj_type):
            ir_type = cx.scope.get_ir_type(cobj_type)
            return compiler.Object(
                cx.builder.alloca(ir_type),
                cobj_type)
            
        return [_make_ir_obj(cobj_type) for cobj_type in return_ctypes]
