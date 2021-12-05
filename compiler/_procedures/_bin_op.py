from __future__ import annotations

from compiler._ir_generation import IRGenerationProcedure
from compiler._context import Context
from compiler._object import Object, Stub
from compiler._options import Options
from compiler._exceptions import Exceptions
from compiler._definitions import Definitions
from compiler._procedures._assigns import assigns_

from seer import Seer
from astnode import AstNode
from error import Raise

from llvmlite import ir

class bin_op_(IRGenerationProcedure):
    matches = [
        "+", "-", "/", "*",
        "<", ">", "<=", ">=",
        "==", "!=",
        "+=", "-=", "/=", "*="
    ]


    @classmethod
    def validate_compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict, 
            options : Options = None) -> list[Object]:

        # start
        op = node.op
        left_cobj = node.left.compile_data[0]
        right_cobj = node.right.compile_data[0]

        exception_msg = ""
        if not left_cobj.is_initialized:
            exception_msg += f"variable '{left_cobj.name}'"

        if not right_cobj.is_initialized:
            if exception_msg:
                exception_msg += " and "
            
            exception_msg += f"variable '{right_cobj.name}'"

        if exception_msg:
            exception = Exceptions.UseBeforeInitialize(
                f"{exception_msg} used here but not initialized",
                node.line_number)

            exception.set_compiler_stub(Stub(left_cobj.type))
            return [exception]

        # validation
        # TODO: assign cobj_type property
        cobj_type = "TODO"
        if   ( op == "+" 
            or op == "-" 
            or op == "*" 
            or op == "/" 
            or op == "+="
            or op == "-="
            or op == "/="
            or op == "*="):

            return [Stub(left_cobj.type)]

        elif   ( op == "=="
            or op == "<="
            or op == ">="
            or op == "<"
            or op == ">"
            or op == "!="):

            return [Stub("#" + Seer.Types.Primitives.Bool)]

        Raise.code_error(f"not implemented binary operation {op}")


    @classmethod
    def compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict, 
            options : Options = None) -> list[Object]:

        op = node.op
        ir_obj = None

        left_compiler_obj = node.left.compile_data[0]
        right_compiler_obj = node.right.compile_data[0]                

        builder_function_params = [
            _deref_ir_obj_if_needed(left_compiler_obj, cx),
            _deref_ir_obj_if_needed(right_compiler_obj, cx)
        ]

        if op == "+":
            ir_obj = cx.builder.add(*builder_function_params)
        elif op == "-":
            ir_obj = cx.builder.sub(*builder_function_params)
        elif op == "*":
            ir_obj = cx.builder.mul(*builder_function_params)
        elif op == "/":
            ir_obj = cx.builder.sdiv(*builder_function_params)

        elif op == "+=" or op == "-=" or op == "*=" or op == "/=":
            ir_obj = None
            op = op[0]
            if op == "+":
                ir_obj = cx.builder.add(*builder_function_params)
            elif op == "-":
                ir_obj = cx.builder.sub(*builder_function_params)
            elif op == "*":
                ir_obj = cx.builder.mul(*builder_function_params)
            elif op == "/":
                ir_obj = cx.builder.sdiv(*builder_function_params)

            new_compiler_obj = Object(
                ir_obj,
                "#" + left_compiler_obj.type)

            return [assigns_._single_assign(
                left_compiler_obj, 
                new_compiler_obj, 
                cx, 
                options)]


        elif(op == "<" 
            or op == ">"
            or op == ">="
            or op == "<="
            or op == "=="
            or op == "!="):
            ir_obj = cx.builder.icmp_signed(op, *builder_function_params)
            return [Object(
                ir_obj,
                "#" + Seer.Types.Primitives.Bool)]
            
        else:
            Raise.code_error(f"op ({op}) is not implemented") 

        return [Object(
            ir_obj,
            "#" + left_compiler_obj.type)]



