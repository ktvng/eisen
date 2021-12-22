from __future__ import annotations

from compiler._ir_generation import IRGenerationProcedure
from compiler._context import Context
from compiler._object import Object, Stub
from compiler._options import Options
from compiler._exceptions import Exceptions
from compiler._definitions import Definitions

from compiler._utils import _deref_ir_obj_if_needed

from astnode import AstNode

from llvmlite import ir

class assigns_(IRGenerationProcedure):
    matches = ["="]

    @classmethod
    def _validate_single_assign(cls,
            node : AstNode,
            left_cobj : Object,
            right_cobj : Object):

        return_objs = []
        if not right_cobj.is_initialized:
            exception = Exceptions.UseBeforeInitialize(
                f"variable {right_cobj.name} is used as assignment value but not initialized",
                node.line_number)

            return_objs.append(exception)
        
        left_cobj.is_initialized = True
        stub_cobj = Stub(left_cobj.type)

        if not Definitions.type_equality(left_cobj.type, right_cobj.type):
            exception = Exceptions.TypeMismatch(
                f"left of expression expects '{left_cobj.type}' but got '{right_cobj.type}' instead",
                node.line_number)
            
            return_objs.append(exception)

        return_objs.append(stub_cobj)
        return return_objs


    @classmethod
    def validate_compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict,
            options : Options=None) -> list[Object]:

        return_objs = []
        
        left_cobjs = node.left.compile_data
        right_cobjs= node.right.compile_data

        left_len = len(left_cobjs)
        right_len = len(right_cobjs)
        if left_len != right_len:
            exception = Exceptions.TupleSizeMismatch(
                f"got size '{left_len}' != '{right_len}'",
                node.line_number)

            return_objs.append(exception)

            # TODO: remove and handle size mismatch
            return return_objs

        # TODO: handle size mismatch
        for left_cobj, right_cobj in zip(left_cobjs, right_cobjs):
            return_objs.extend(
                cls._validate_single_assign(node, left_cobj, right_cobj))

        return return_objs

    @classmethod
    def _single_assign(cls, 
            left_compiler_obj, 
            right_compiler_obj, 
            cx : Context, 
            options : Options):

        left_compiler_obj.is_initialized=True
        ir_obj_to_assign = _deref_ir_obj_if_needed(right_compiler_obj, cx)
        return Object(
            cx.builder.store(ir_obj_to_assign, left_compiler_obj.get_ir()),
            left_compiler_obj.type)


    @classmethod
    def compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict, 
            options : Options = None) -> list[Object]:

        left_compiler_objs = node.left.compile_data
        right_compiler_objs = node.right.compile_data

        compiler_objs = []
        for left_compiler_obj, right_compiler_obj in zip(left_compiler_objs, right_compiler_objs):
            compiler_objs.append(
                cls._single_assign(left_compiler_obj, right_compiler_obj, cx, options))

        return compiler_objs
