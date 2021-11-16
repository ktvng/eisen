from __future__ import annotations
from ast import AstNode
import ast
from llvmlite import ir
from error import Raise

class Compiler():
    def __init__(self, asthead : AstNode):
        self.asthead = asthead
        self._build_parse_map()
        self._global_functions = Compiler.functions_scope()
        self._gloabl_vars = Compiler.variables_scope()

    @classmethod
    def _build_parse_map(cls):
        cls.parse_classes = [
            Compiler.start,
            Compiler.return_,
            Compiler.function,
            Compiler.function_call,
            Compiler.codeblock,
            Compiler.var_decl,
            Compiler.var,
            Compiler.tuple_,
            Compiler.string_,
            Compiler.params_decl,
            Compiler.tag,
            Compiler.return_decl,
        ]

        cls.parse_map = {}
        for klass in cls.parse_classes:
            for match in klass.matches:
                cls.parse_map[match] = klass


    def run(self) -> str:
        mod = ir.Module()
        global_scope = Compiler.Scope(mod, None)
        self._recursive_descent(self.asthead, global_scope)
        return str(mod)

    @classmethod
    def _recursive_descent(cls, node : AstNode, scope : Compiler.Scope):
        compile_with_class = cls.parse_map[node.op]

        new_scope, args = compile_with_class.precompile(node, scope)

        # recurse the children
        for child in node.vals:
            cls._recursive_descent(child, new_scope)
        
        compile_with_class.compile(node, new_scope, args)





    ################################################################################################
    # Internal tooling

    class types():
        i32 = ir.IntType(32)
        i8 = ir.IntType(8)

        @classmethod
        def get_by_name(cls, name : str):
            if name == "int":
                return Compiler.types.i8

    class functions_scope():
        def __init__(self):
            self.name_map = {}
            self.parent_scope = None

        def add(cls, name : str, func):
            pass

        def get(cls, name : str):
            pass

    class variables_scope():
        def __init__(self):
            self.variables_map = {}
            self.parent_scope = None

        def add(self, name : str, var):
            self.variables[name] = var

        def get(self, name):
            found = self.variables_map.get(name, None)
            if found is not None:
                return found
            
            Raise.error(f"could not find variable {name}")

            


    class Scope():
        def __init__(self, mod : ir.Module, builder : ir.IRBuilder):
            self.functions = Compiler.functions_scope()
            self.variables = Compiler.variables_scope()
            self.module = mod
            self.builder = builder
            self.func = None

        def get_function_by_fqname(self, name : str):
            pass

        def get_variable_by_fqname(self, name : str):
            return self.variables.get(name)

        def get_type_of_variable_by_name(self, name : str):
            # TODO: finish
            if name == "int":
                return Compiler.types.i8
            else:
                Raise.code_error(f"{name} for unfinished get_type_of_variable_by_name")
            
        









    class CodeGenerationProcedure():
        @classmethod
        def precompile(cls, node : AstNode, s : Compiler.Scope):
            return s, []
        
        @classmethod
        def compile(cls, node : AstNode, s : Compiler.Scope, args : list):
            return

    ################################################################################################
    # Code generation behavior

    class start(CodeGenerationProcedure):
        matches = ["start"]

    class codeblock(CodeGenerationProcedure):
        matches = ["codeblock"]

    # TODO: impl
    class return_(CodeGenerationProcedure):
        matches = ["return"]

        @classmethod
        def handle_deallocation():
            pass

        @classmethod
        def get_heap_pointer_stack():
            pass

        @classmethod
        def compile(cls, node : AstNode, s : Compiler.Scope, args : list):
            node.compile_data = s.builder.ret_void()

    # TODO: impl RVO
    class function(CodeGenerationProcedure):
        matches = ["function"]

        @classmethod
        def precompile(cls, node: AstNode, s : Compiler.Scope):
            # don't compile the final codeblock
            for child in node.vals[: -1]:
                Compiler._recursive_descent(child, s)

            # TODO: impl
            func_type = ir.FunctionType(ir.VoidType(), ())
            func_name = node.vals[0].compile_data
            func = ir.Function(s.module, func_type, name=func_name)

            builder = ir.IRBuilder(func.append_basic_block("entry"))
            new_scope = Compiler.Scope(s.module, builder)
            node.compile_data = func

            return new_scope, []

        @classmethod
        def compile(cls, node: AstNode, s: Compiler.Scope, args: list):
            s.builder.ret_void()
    
    class function_call(CodeGenerationProcedure):
        matches = ["function_call"]

        @classmethod
        def compile(cls, node : AstNode, s : Compiler.Scope, args : list):
            func = node.vals[0].compile_data
            params = node.vals[1].compile_data

            # TODO: make clean
            if func == Compiler.var.special.get("print", s):
                c_str_val = params[0] #args will be passed into printf function.

                c_str = s.builder.alloca(c_str_val.type) #creation of the allocation of the %".2" variable
                s.builder.store(c_str_val, c_str) #store as defined on the next line below %".2"

                voidptr_ty = ir.IntType(8).as_pointer() 
                node.compile_data = s.builder.call(func, [c_str]) #We are calling the prinf function with the fmt and arg and returning the value as defiend on the next line
                return

            node.compile_data = s.builder.call(func, params)

    class tuple_(CodeGenerationProcedure):
        matches = ["tuple"]

        @classmethod
        def compile(cls, node: AstNode, s: Compiler.Scope, args: list):
            node.compile_data = [child.compile_data for child in node.vals]

    class var_decl(CodeGenerationProcedure):
        matches = [":"]

        @classmethod
        def compile(cls, node : AstNode, s : Compiler.Scope, args : list):
            name = node.vals[0].compile_data
            type_str = node.vals[1].compile_data
            var_type = s.get_type_of_variable_by_name(type_str)

            node.compile_data = s.builder.alloca(var_type, name=name)

    class binary_op(CodeGenerationProcedure):
        matches = [
            "+", "-", "/", "*",
            "<", ">", "<=", ">=",
            "==", "!=",
            "="
        ]

        @classmethod
        def compile(cls, node : AstNode, s: Compiler.Scope, args : list):
            op = node.op

            params = (node.left.data, node.right.data)
            if op == "+":
                node.compile_data = s.builder.add(*params)
            elif op == "-":
                node.compile_data = s.builder.sub(*params)
            elif op == "*":
                node.compile_data = s.builder.mul(*params)
            elif op == "/":
                node.compile_data = s.builder.sdiv(*params)

            elif(op == "<" 
                or op == ">"
                or op == ">="
                or op == "<="
                or op == "=="
                or op == "!="):
                node.compile_data = s.builder.icmp_signed(op, *params)

            elif op == "=":
                node.compile_data = s.builder.store(node.right.data, node.left.data)
            else:
                Raise.code_error(f"op ({op}) is not implemented")


    class var(CodeGenerationProcedure):
        matches = ["var"]

        @classmethod
        def compile(cls, node: AstNode, s: Compiler.Scope, args: list):
            name = node.leaf_val

            # special variables looked up statically
            if Compiler.var.is_special(name):
                node.compile_data = Compiler.var.special.get(name, s)
                return

            # variables are resolved inside a scope
            node.compile_data = s.get_variable_by_fqname(name);
            
        @classmethod
        def is_special(cls, name : str):
            return name in Compiler.var.special.names
            
        class special():
            names = ["print", "int"]

            @classmethod
            def get(cls, func_name : str, s : Compiler.Scope):
                # TODO: make this cleaner
                if func_name == "print":
                    return Compiler.var.special.print.get(s.module)
                elif func_name == "int":
                    return "int" 

            @classmethod
            class print():
                is_init = False
                print_func = None

                @classmethod
                def init(cls, mod : ir.Module):
                    if cls.is_init:
                        return

                    cls.is_init = True
                    print_type = ir.FunctionType(ir.IntType(32), [], var_arg=True)
                    print_func = ir.Function(mod, print_type, name="printf")

                    cls.print_func = print_func

                @classmethod
                def get(cls, mod):
                    cls.init(mod)
                    return cls.print_func
                
    class string_(CodeGenerationProcedure):
        matches = ["string"]

        @classmethod
        def compile(cls, node: AstNode, s: Compiler.Scope, args: list):
            str_data = node.literal_val + "\0"
            node.compile_data = ir.Constant(
                ir.ArrayType(Compiler.types.i8, len(str_data)), 
                bytearray(str_data.encode("utf8")))
            
    class params_decl(CodeGenerationProcedure):
        matches = ["params_decl"]

        @classmethod
        def compile(cls, node: AstNode, s: Compiler.Scope, args: list):
            # TODO: implement
            node.compile_data = []

    class tag(CodeGenerationProcedure):
        matches = ["tag"]

        @classmethod
        def compile(cls, node: AstNode, s: Compiler.Scope, args: list):
            node.compile_data = node.leaf_val

    # TODO: implement RVO
    # TODO: change when -> is removed from AST
    class return_decl(CodeGenerationProcedure):
        matches = ["return_decl"]

        @classmethod
        def compile(cls, node: AstNode, s: Compiler.Scope, args: list):
            pass
