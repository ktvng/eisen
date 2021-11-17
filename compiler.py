from __future__ import annotations
from seer import Seer
from ast import AstNode
import ast
from llvmlite import ir
from error import Raise

class Compiler():
    def __init__(self, asthead : AstNode):
        self.asthead = asthead
        self._build_parse_map()
        self._gloabl_vars = Compiler.variables_scope()
        self.defaults = {
            Seer.Types.Primitives.Int: Compiler.Variable(ir.Constant(ir.IntType(32), 0), Seer.Types.Primitives.Int)
        }

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
            Compiler.int_,
            Compiler.binary_op,
            Compiler.assigns,
            Compiler.bool_,
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
        compile_with_class = cls.parse_map.get(node.op, None)
        if compile_with_class is None:
            Raise.code_error(f"key error on {node.op} in the parse_map. Make a Compiler.{node.op}_ class and add it to the list")

        new_scope, args = compile_with_class.precompile(node, scope)

        # recurse the children
        for child in node.vals:
            cls._recursive_descent(child, new_scope)
        
        compile_with_class.compile(node, new_scope, args)

    @classmethod
    def _get_code_variables_from_compiler_variables(cls, compiler_vars : list, s : Compiler.Scope):
        code_vars = []
        for var in compiler_vars:
            if var.type_name == Seer.Types.Primitives.Int:
                code_vars.append(s.builder.load(var.value))
            else:
                code_vars.append(var.value)

        return code_vars

    ################################################################################################
    # Internal tooling

    class types():
        i32 = ir.IntType(32)
        i8 = ir.IntType(8)
        bool = ir.IntType(8)

        @classmethod
        def get_by_name(cls, name : str):
            if name == Seer.Types.Primitives.Int:
                return Compiler.types.i32

    class variables_scope():
        def __init__(self):
            self.variables_map = {}
            self.parent_scope = None

        def add(self, name : str, variable : Compiler.Variable):
            self.variables_map[name] = variable

        def get(self, name):
            found = self.variables_map.get(name, None)
            if found is not None:
                return found
        

    class Variable():
        modifiers = ["?", "!", ""]
        def __init__(self, value, type_name, modifier=""):
            self.value = value
            self.type_name = type_name

            if modifier not in modifier:
                Raise.code_error("invalid modifier")
            
            self.modifier = modifier

    class Function():
        def __init__(self, value, params, returns):
            self.value = value
            self.params = params
            self.returns = returns



    class Scope():
        def __init__(self, mod : ir.Module, builder : ir.IRBuilder, parent_scope = None):
            self.variables = Compiler.variables_scope()
            self.module = mod
            self.builder = builder
            self.func = None
            self.parent_scope = parent_scope

        def get_function_by_fqname(self, name : str):
            pass

        def get_variable_by_fqname(self, name : str):
            var = self.variables.get(name)
            if var is None and self.parent_scope is not None:
                var = self.parent_scope.get_variable_by_fqname(name) 

            if var is None:
                Raise.error(f"could not find variable {name}")

            return var

        def get_type_of_variable_by_name(self, name : str):
            # TODO: finish, duplicated, search Seer.Types.Primitives.Int
            if name == Seer.Types.Primitives.Int:
                return Compiler.types.i32
            elif name == Seer.Types.Primitives.Bool:
                return Compiler.types.i8
            else:
                Raise.code_error(f"{name} for unfinished get_type_of_variable_by_name")

        def add_variable(self, var, var_name, type_name, modifier=""):
            variable = Compiler.Variable(var, type_name, modifier)
            self.variables.add(var_name, variable)

            return variable
            
        









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

    class return_(CodeGenerationProcedure):
        matches = ["return"]

        # TODO: impl
        @classmethod
        def handle_deallocation():
            pass

        @classmethod
        def get_heap_pointer_stack():
            pass

        @classmethod
        def compile(cls, node : AstNode, s : Compiler.Scope, args : list):
            s.builder.ret_void()
            Compiler._let_node_return_nothing()

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

            s.add_variable(func, func_name, str(func_type))

            builder = ir.IRBuilder(func.append_basic_block("entry"))
            new_scope = Compiler.Scope(s.module, builder, parent_scope=s)
            node.compile_data = func

            return new_scope, []

        @classmethod
        def compile(cls, node: AstNode, s: Compiler.Scope, args: list):
            if(not s.builder.block.is_terminated):
                s.builder.ret_void()
    
    class function_call(CodeGenerationProcedure):
        matches = ["function_call"]

        @classmethod
        def compile(cls, node : AstNode, s : Compiler.Scope, args : list):
            func = node.vals[0].compile_data.value
            compiler_param_vars = node.vals[1].compile_data
            code_param_vars = Compiler._get_code_variables_from_compiler_variables(compiler_param_vars, s)
            node.compile_data = s.builder.call(func, code_param_vars)

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
            code_var_type = s.get_type_of_variable_by_name(type_str)

            code_var = s.builder.alloca(code_var_type, name=name)

            # TODO: add modifier
            variable = s.add_variable(code_var, name, type_str)

            node.compile_data = variable

    class binary_op(CodeGenerationProcedure):
        matches = [
            "+", "-", "/", "*",
            "<", ">", "<=", ">=",
            "==", "!=",
        ]

        @classmethod
        def compile(cls, node : AstNode, s: Compiler.Scope, args : list):
            op = node.op

            newvar = None
            code_params = Compiler._get_code_variables_from_compiler_variables([node.left.compile_data, node.right.compile_data], s)
            if op == "+":
                newvar = s.builder.add(*code_params)
            elif op == "-":
                newvar = s.builder.sub(*code_params)
            elif op == "*":
                newvar = s.builder.mul(*code_params)
            elif op == "/":
                newvar = s.builder.sdiv(*code_params)

            elif(op == "<" 
                or op == ">"
                or op == ">="
                or op == "<="
                or op == "=="
                or op == "!="):
                newvar = s.builder.icmp_signed(op, *code_params)
                node.compile_data = Compiler.Variable(newvar, Seer.Types.Primitives.Bool)
                return
                
            else:
                Raise.code_error(f"op ({op}) is not implemented") 

            node.compile_data = Compiler.Variable(newvar, node.left.compile_data.type_name + "_literal")

    class var(CodeGenerationProcedure):
        matches = ["var"]
        primitives = ["int"]
                
        @classmethod
        def compile(cls, node: AstNode, s: Compiler.Scope, args: list):
            name = node.leaf_val

            # special variables looked up statically
            if Compiler.var.is_special(name):
                node.compile_data = Compiler.var.special.get(name, s)
                return

            # variables are resolved inside a scope
            node.compile_data = s.get_variable_by_fqname(name)
            
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

                    cls.print_func = Compiler.Variable(print_func, str(print_func.type))

                @classmethod
                def get(cls, mod):
                    cls.init(mod)
                    return cls.print_func
                
    class string_(CodeGenerationProcedure):
        matches = ["string"]

        @classmethod
        def compile(cls, node: AstNode, s: Compiler.Scope, args: list):
            str_data = node.literal_val + "\0"
            c_str_val = ir.Constant(
                ir.ArrayType(Compiler.types.i8, len(str_data)), 
                bytearray(str_data.encode("utf8")))
            
            c_str = s.builder.alloca(c_str_val.type) #creation of the allocation of the %".2" variable
            s.builder.store(c_str_val, c_str) #store as defined on the next line below %".2"
            
            node.compile_data = Compiler.Variable(c_str, "string")
            
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

    class int_(CodeGenerationProcedure):
        matches = ["int"]

        @classmethod
        def compile(cls, node: AstNode, s: Compiler.Scope, args: list):
            node.compile_data = Compiler.Variable(
                ir.Constant(Compiler.types.i32, int(node.literal_val)),
                "int_literal")

    class assigns(CodeGenerationProcedure):
        matches = ["="]

        @classmethod
        def compile(cls, node: AstNode, s: Compiler.Scope, args: list):
            code_int_ptr = node.left.compile_data.value
            code_int_val = Compiler._get_code_variables_from_compiler_variables([node.right.compile_data], s)[0]
            node.compile_data = s.builder.store(code_int_val, code_int_ptr)

    class bool_(CodeGenerationProcedure):
        matches = ["bool"]

        @classmethod
        def compile(cls, node: AstNode, s: Compiler.Scope, args: list):
            value = None
            if node.literal_val == Seer.Constants.true:
                value = 1
            elif node.literal_val == Seer.Constants.false:
                value = 0
            else:
                Raise.error("bool must be true or false")

            node.compile_data = Compiler.Variable(
                ir.Constant(Compiler.types.i8, value),
                "bool_literal")