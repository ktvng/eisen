from __future__ import annotations

import alpaca.compiler as compiler
from seer._utils import _deref_ir_obj_if_needed
from seer._definitions import Definitions
from alpaca.asts import ASTNode

class assigns_(compiler.IRGenerationProcedure):
    matches = ["="]

    @classmethod
    def _validate_single_assign(cls,
            node : ASTNode,
            left_cobj : compiler.Object,
            right_cobj : compiler.Object):

        return_objs = []
        if not right_cobj.is_initialized:
            exception = compiler.Exceptions.UseBeforeInitialize(
                f"variable {right_cobj.name} is used as assignment value but not initialized",
                node.line_number)

            return_objs.append(exception)
        
        left_cobj.is_initialized = True
        stub_cobj = compiler.Stub(left_cobj.type)

        if not Definitions.type_equality(left_cobj.type, right_cobj.type):
            exception = compiler.Exceptions.TypeMismatch(
                f"left of expression expects '{left_cobj.type}' but got '{right_cobj.type}' instead",
                node.line_number)
            
            return_objs.append(exception)

        return_objs.append(stub_cobj)
        return return_objs


    @classmethod
    def validate_compile(cls, 
            node : ASTNode, 
            cx : compiler.Context, 
            args : dict,
            options : compiler.Options=None) -> list[compiler.Object]:

        return_objs = []
        
        left_cobjs = node.children[0].compile_data
        right_cobjs= node.children[1].compile_data

        left_len = len(left_cobjs)
        right_len = len(right_cobjs)
        if left_len != right_len:
            exception = compiler.Exceptions.TupleSizeMismatch(
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
            cx : compiler.Context, 
            options : compiler.Options):

        left_compiler_obj.is_initialized=True
        ir_obj_to_assign = _deref_ir_obj_if_needed(right_compiler_obj, cx)
        return compiler.Object(
            cx.builder.store(ir_obj_to_assign, left_compiler_obj.get_ir()),
            left_compiler_obj.type)


    @classmethod
    def compile(cls, 
            node : ASTNode, 
            cx : compiler.Context, 
            args : dict, 
            options : compiler.Options = None) -> list[compiler.Object]:

        left_compiler_objs = node.children[0].compile_data
        right_compiler_objs = node.children[1].compile_data

        compiler_objs = []
        for left_compiler_obj, right_compiler_obj in zip(left_compiler_objs, right_compiler_objs):
            compiler_objs.append(
                cls._single_assign(left_compiler_obj, right_compiler_obj, cx, options))

        return compiler_objs
