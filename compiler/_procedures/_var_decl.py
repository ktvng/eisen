from __future__ import annotations

from compiler._ir_generation import IRGenerationProcedure
from compiler._context import Context
from compiler._object import Object, Stub
from compiler._options import Options

from astnode import AstNode

from llvmlite import ir

class var_decl_(IRGenerationProcedure):
    matches = [":"]

    @classmethod
    def _get_cobj_type(cls, node : AstNode) -> str:
        return node.vals[1].compile_data[0].get_tag_value()

    @classmethod
    def _get_cobj_names(cls, node : AstNode) -> list[str]:
        cobjs_storing_names = node.vals[0].compile_data
        return [cobj.get_tag_value() for cobj in cobjs_storing_names]

    @classmethod
    def _add_new_cobj_to_scope(cls, cobjs : list[Object], cx : Context):
        for cobj in cobjs:
            cx.scope.add_obj(cobj.name, cobj)

    @classmethod
    def validate_compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict,
            options : Options=None) -> list[Object]:

        cobj_type = cls._get_cobj_type(node)
        cobj_names = cls._get_cobj_names(node)

        new_cobjs = [Stub(cobj_type, name) for name in cobj_names]
        cls._add_new_cobj_to_scope(new_cobjs, cx)

        return new_cobjs

    @classmethod
    def compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict, 
            options : Options = None) -> list[Object]:

        cobj_type = cls._get_cobj_type(node)
        cobj_names = cls._get_cobj_names(node)
        ir_type = cx.scope.get_ir_type(cobj_type)

        new_cobjs = [   Object(
                            cx.builder.alloca(ir_type, name=name),
                            cobj_type,
                            name=name)
                        for name in cobj_names]
        
        cls._add_new_cobj_to_scope(new_cobjs, cx)

        return new_cobjs


class let_(IRGenerationProcedure):
    matches = ["let"]

    @classmethod
    def validate_compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict, 
            options : Options = None) -> list[Object]:

        compiler_objs = var_decl_.validate_compile(node, cx, args, options)
        for obj in compiler_objs:
            obj.is_initialized = False

        return compiler_objs

    @classmethod
    def compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict, 
            options : Options = None) -> list[Object]:

        return var_decl_.compile(node, cx, args, options)
        