from __future__ import annotations

from compiler._ir_generation import IRGenerationProcedure
from compiler._context import Context
from compiler._object import Object, Stub
from compiler._options import Options
from compiler._definitions import Definitions
from compiler._ir_types import IrTypes
from compiler._exceptions import Exceptions

from astnode import AstNode
from seer import Seer

from llvmlite import ir

class string_(IRGenerationProcedure):
    matches = ["string"]

    @classmethod
    def _get_cobj_type(cls):
        return Seer.Types.Primitives.String

    @classmethod
    def validate_compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict,
            options : Options=None) -> list[Object]:

        cobj_type = cls._get_cobj_type()
        return [Stub(cobj_type)]
        
    @classmethod
    def compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict, 
            options : Options = None) -> list[Object]:

        cobj_type = cls._get_cobj_type()
        str_data = node.literal_val + "\0"
        c_str_data = ir.Constant(
            ir.ArrayType(IrTypes.char, 
            len(str_data)), 
            bytearray(str_data.encode("utf8")))
        
        c_str = cx.builder.alloca(c_str_data.type)
        cx.builder.store(c_str_data, c_str)
        
        return [Object(
            c_str,
            cobj_type)]


class int_(IRGenerationProcedure):
    matches = ["int"]

    @classmethod
    def _get_cobj_type(cls) -> str:
        return "#" + Seer.Types.Primitives.Int

    @classmethod
    def validate_compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict,
            options : Options=None) -> list[Object]:

        cobj_type = cls._get_cobj_type()
        return [Stub(cobj_type)]

    @classmethod
    def compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict, 
            options : Options = None) -> list[Object]:

        cobj_type = cls._get_cobj_type()
        return [Object(
            ir.Constant(IrTypes.int, int(node.literal_val)),
            cobj_type)]


class bool_(IRGenerationProcedure):
    matches = ["bool"]

    @classmethod
    def _get_cobj_type(cls) -> str:
        return "#" + Seer.Types.Primitives.Bool

    @classmethod
    def validate_compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict,
            options : Options=None) -> list[Object]: 

        cobj_type = cls._get_cobj_type()
        return [Stub(cobj_type)]

    
    @classmethod
    def compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict, 
            options : Options = None) -> list[Object]:

        cobj_type = cls._get_cobj_type()
        return [Object(
            ir.Constant(IrTypes.bool, True if node.literal_val == "true" else False),
            cobj_type)]


class tag_(IRGenerationProcedure):
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
            cx : Context, 
            args : dict,
            options : Options=None) -> list[Object]:

        # start
        cobj_type = cls._get_cobj_type()
        tag_name = cls._get_tag_name(node)

        stub_obj = Stub(cobj_type)
        stub_obj.set_tag_value(tag_name)

        return [stub_obj]


    @classmethod
    def compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict, 
            options : Options = None) -> list[Object]:

        cobj_type = cls._get_cobj_type()
        return [Object(
            cls._get_tag_name(node),
            cobj_type)]


class var_(IRGenerationProcedure):
    matches = ["var"]

    @classmethod
    def _get_name_and_cobj(cls, node : AstNode, cx : Context
            ) -> tuple[str, Object]:
        
        name = node.leaf_val
        cobj = cx.scope.get_object(name)

        return name, cobj

    @classmethod
    def validate_compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict,
            options : Options=None) -> list[Object]:

        name, cobj = cls._get_name_and_cobj(node, cx)
        if cobj is None:
            exception = Exceptions.UndefinedVariable(
                f"variable '{name}' is not defined", 
                node.line_number)

            # TODO: formalize this convention; if a variable is undefined we need to pass up an
            # object with at least some type
            exception.set_compiler_stub(Stub("???", name=name))
            return [exception]
            
        return [cobj]

    @classmethod
    def compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict, 
            options : Options = None) -> list[Object]:
            
        name, cobj = cls._get_name_and_cobj(node, cx)
        return [cobj]
