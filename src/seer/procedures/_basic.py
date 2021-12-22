from __future__ import annotations

import compiler
from ast import AstNode
from seer import Seer
from seer._definitions import Definitions
from llvmlite import ir

class string_(compiler.IRGenerationProcedure):
    matches = ["string"]

    @classmethod
    def _get_cobj_type(cls):
        return Seer.Types.Primitives.String

    @classmethod
    def validate_compile(cls, 
            node : AstNode, 
            cx : compiler.Context, 
            args : dict,
            options : compiler.Options=None) -> list[compiler.Object]:

        cobj_type = cls._get_cobj_type()
        return [compiler.Stub(cobj_type)]
        
    @classmethod
    def compile(cls, 
            node : AstNode, 
            cx : compiler.Context, 
            args : dict, 
            options : compiler.Options = None) -> list[compiler.Object]:

        cobj_type = cls._get_cobj_type()
        str_data = node.literal_val + "\0"
        c_str_data = ir.Constant(
            ir.ArrayType(compiler.IrTypes.char, 
            len(str_data)), 
            bytearray(str_data.encode("utf8")))
        
        c_str = cx.builder.alloca(c_str_data.type)
        cx.builder.store(c_str_data, c_str)
        
        return [compiler.Object(
            c_str,
            cobj_type)]


class int_(compiler.IRGenerationProcedure):
    matches = ["int"]

    @classmethod
    def _get_cobj_type(cls) -> str:
        return "#" + Seer.Types.Primitives.Int

    @classmethod
    def validate_compile(cls, 
            node : AstNode, 
            cx : compiler.Context, 
            args : dict,
            options : compiler.Options=None) -> list[compiler.Object]:

        cobj_type = cls._get_cobj_type()
        return [compiler.Stub(cobj_type)]

    @classmethod
    def compile(cls, 
            node : AstNode, 
            cx : compiler.Context, 
            args : dict, 
            options : compiler.Options = None) -> list[compiler.Object]:

        cobj_type = cls._get_cobj_type()
        return [compiler.Object(
            ir.Constant(compiler.IrTypes.int, int(node.literal_val)),
            cobj_type)]


class bool_(compiler.IRGenerationProcedure):
    matches = ["bool"]

    @classmethod
    def _get_cobj_type(cls) -> str:
        return "#" + Seer.Types.Primitives.Bool

    @classmethod
    def validate_compile(cls, 
            node : AstNode, 
            cx : compiler.Context, 
            args : dict,
            options : compiler.Options=None) -> list[compiler.Object]: 

        cobj_type = cls._get_cobj_type()
        return [compiler.Stub(cobj_type)]

    
    @classmethod
    def compile(cls, 
            node : AstNode, 
            cx : compiler.Context, 
            args : dict, 
            options : compiler.Options = None) -> list[compiler.Object]:

        cobj_type = cls._get_cobj_type()
        return [compiler.Object(
            ir.Constant(compiler.IrTypes.bool, True if node.literal_val == "true" else False),
            cobj_type)]


class tag_(compiler.IRGenerationProcedure):
    matches = ["tag"]

    @classmethod
    def _get_cobj_type(cls) -> str:
        return Definitions.reference_type

    @classmethod
    def _get_tag_name(cls, node : AstNode) -> str:
        return node.leaf_val

    @classmethod
    def validate_compile(cls, 
            node : AstNode, 
            cx : compiler.Context, 
            args : dict,
            options : compiler.Options=None) -> list[compiler.Object]:

        # start
        cobj_type = cls._get_cobj_type()
        tag_name = cls._get_tag_name(node)

        stub_obj = compiler.Stub(cobj_type)
        stub_obj.set_tag_value(tag_name)

        return [stub_obj]


    @classmethod
    def compile(cls, 
            node : AstNode, 
            cx : compiler.Context, 
            args : dict, 
            options : compiler.Options = None) -> list[compiler.Object]:

        cobj_type = cls._get_cobj_type()
        return [compiler.Object(
            cls._get_tag_name(node),
            cobj_type)]


class var_(compiler.IRGenerationProcedure):
    matches = ["var"]

    @classmethod
    def _get_name_and_cobj(cls, node : AstNode, cx : compiler.Context
            ) -> tuple[str, compiler.Object]:
        
        name = node.leaf_val
        cobj = cx.scope.get_object(name)

        return name, cobj

    @classmethod
    def validate_compile(cls, 
            node : AstNode, 
            cx : compiler.Context, 
            args : dict,
            options : compiler.Options=None) -> list[compiler.Object]:

        name, cobj = cls._get_name_and_cobj(node, cx)
        if cobj is None:
            exception = compiler.Exceptions.UndefinedVariable(
                f"variable '{name}' is not defined", 
                node.line_number)

            # TODO: formalize this convention; if a variable is undefined we need to pass up an
            # object with at least some type
            exception.set_compiler_stub(compiler.Stub("???", name=name))
            return [exception]
            
        return [cobj]

    @classmethod
    def compile(cls, 
            node : AstNode, 
            cx : compiler.Context, 
            args : dict, 
            options : compiler.Options = None) -> list[compiler.Object]:
            
        name, cobj = cls._get_name_and_cobj(node, cx)
        return [cobj]
