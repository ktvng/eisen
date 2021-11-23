from __future__ import annotations
from seer import Seer
from ast import AstNode
import ast
from llvmlite import ir
from error import Raise

class Compiler():
    verbose = True

    def __init__(self, asthead : AstNode):
        self.asthead = asthead
        self.mod = ir.Module()
        self.global_scope = Compiler.Scope(self.mod, None)

        self._add_primitive_types(self.global_scope)

        self.defaults = None
        self._add_defaults()
        self.parse_map = None
        self._build_parse_map()

    def _add_defaults(self):
        self.defaults = {
            Seer.Types.Primitives.Int: Compiler.Variable(
                ir.Constant(ir.IntType(32), 0), 
                self.global_scope.get_defined_type(Seer.Types.Primitives.Int)),
        
            Seer.Types.Primitives.Float: Compiler.Variable(
                ir.Constant(ir.FloatType(), 0), 
                self.global_scope.get_defined_type(Seer.Types.Primitives.Float)),

            Seer.Types.Primitives.Bool: Compiler.Variable(
                ir.Constant(Compiler.types.bool, 0), 
                self.global_scope.get_defined_type(Seer.Types.Primitives.Bool)),
        }

    def _build_parse_map(self):
        self.parse_classes = [
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

        self.parse_map = {}
        for klass in self.parse_classes:
            for match in klass.matches:
                cls.parse_map[match] = klass


    def run(self) -> str:
        self._recursive_descent(self.asthead, self.global_scope)
        return str(self.mod)

    def _add_primitive_types(self, global_scope : Compiler.Scope):
        global_scope.add_type("int", Compiler.PrimitiveType("int"))
        global_scope.add_type("float", Compiler.PrimitiveType("float"))
        global_scope.add_type("str", Compiler.PrimitiveType("str"))
        global_scope.add_type("bool", Compiler.PrimitiveType("bool"))
        global_scope.add_type("int_literal", Compiler.PrimitiveType("int_literal"))

    @classmethod
    def _verbose_status(cls, msg : str,  head : AstNode, node : AstNode, scope : Compiler.Scope):  
        str_rep = head.rs_to_string("", 0, node)

        print("================================")
        print(msg)
        print(str_rep)


    def _recursive_descent(self, node : AstNode, scope : Compiler.Scope):
        compile_with_class = self.parse_map.get(node.op, None)
        if compile_with_class is None:
            Raise.code_error(f"key error on {node.op} in the parse_map. Make a Compiler.{node.op}_ class and add it to the list")

        if Compiler.verbose:
            Compiler._verbose_status("Precompiling", self.asthead, node, scope)

        new_scope, args = compile_with_class.precompile(node, scope)

        # recurse the children
        for child in node.vals:
            self._recursive_descent(child, new_scope)

        if Compiler.verbose:
            Compiler._verbose_status("Compiling", self.asthead, node, scope)
        
        compile_with_class.compile(node, new_scope, args)

    @classmethod
    def _get_ir_variables_from_compiler_variables(cls, compiler_objs : list, s : Compiler.Scope):
        ir_objs = []
        for var in compiler_objs:
            if var.type == s.get_defined_type(Seer.Types.Primitives.Int):
                ir_objs.append(s.builder.load(var.ir_obj))
            else:
                ir_objs.append(var.ir_obj)

        return ir_objs

    ################################################################################################
    # Internal tooling

    class types():
        i32 = ir.IntType(32)
        i8 = ir.IntType(8)
        bool = ir.IntType(1)

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
            
            return None
    class Type():
        def __init__(self):
            self._value = None

        def value():
            pass

        def __eq__(a, b):
            return (isinstance(a, Compiler.Type) 
                and isinstance(b, Compiler.Type) 
                and a.value() == b.value())

        def value(self):
            return self._value()
    class FunctionType(Type):
        def __init__(self, param_types : list, return_types : list):
            self.param_types = param_types
            self.return_types = return_types

        def value(self):
            return ("(" 
                + ", ".join(list(map(lambda x : x.value(), self.param_types))) 
                + ") -> ("
                + ", ".join(list(map(lambda x : x.value(), self.return_types)))
                + ")")

    class PrimitiveType(Type):
        primitives = [
            Seer.Types.Primitives.Bool,
            Seer.Types.Primitives.Float,
            Seer.Types.Primitives.Int,
            Seer.Types.Primitives.String,
            "int_literal",
            "str_literal",
        ]

        def __init__(self, type_str : str):
            if type_str not in self.primitives:
                Raise.code_error("primitive not recognized")
            
            self._value = type_str


        


    class Object():
        def __init__(self, ir_obj, type : Compiler.Type):
            self.ir_obj = ir_obj
            self.type = type   

        def get_ir_obj(self):
            return self.ir_obj

        def __str__(self):
            return str(self.ir_obj)

        
    class Variable(Object):
        modifiers = ["?", "!", ""]

        def __init__(self, ir_obj, type : Compiler.Type, modifier : str = ""):
            super().__init__(ir_obj, type)
            
            if modifier not in Compiler.Variable.modifiers:
                Raise.code_error("invalid modifier")
            
            self.modifier = modifier

        def __str__(self):
            return f"var {str(self.ir_obj)}"
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
            self.defined_types = {}

        def get_variable_by_fqname(self, name : str):
            var = self.variables.get(name)
            if var is None and self.parent_scope is not None:
                var = self.parent_scope.get_variable_by_fqname(name) 

            if var is None:
                Raise.error(f"could not find variable {name}")

            return var

        def add_type(self, name : str, type : Compiler.Type):
            self.defined_types[name] = type

        def get_defined_type(self, name : str):
            type = self.defined_types.get(name, None)
            if type is None and self.parent_scope is not None:
                type = self.parent_scope.get_defined_type(name)

            if type is None:
                Raise.error(f"could not find type {name}")
            
            return type

        def get_type_of_variable_by_name(self, name : str):
            # TODO: finish, duplicated, search Seer.Types.Primitives.Int
            if name == Seer.Types.Primitives.Int:
                return Compiler.types.i32
            elif name == Seer.Types.Primitives.Bool:
                return Compiler.types.bool
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
            func = node.vals[0].compile_data.ir_obj
            compiler_param_vars = node.vals[1].compile_data
            code_param_vars = Compiler._get_ir_variables_from_compiler_variables(compiler_param_vars, s)
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
            code_params = Compiler._get_ir_variables_from_compiler_variables([node.left.compile_data, node.right.compile_data], s)
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
                node.compile_data = Compiler.Variable(
                    newvar, 
                    s.get_defined_type(Seer.Types.Primitives.Bool))

                return
                
            else:
                Raise.code_error(f"op ({op}) is not implemented") 

            node.compile_data = Compiler.Variable(
                newvar, 
                s.get_defined_type(node.left.compile_data.type_name + "_literal"))

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

                    cls.print_func = Compiler.Function(
                        print_func,

                        s.get_defined_type(str(print_func.type)))

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
            
            node.compile_data = Compiler.Variable(
                c_str,
                s.get_defined_type("str"))
            
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
                s.get_defined_type("int_literal"))

    class assigns(CodeGenerationProcedure):
        matches = ["="]

        @classmethod
        def compile(cls, node: AstNode, s: Compiler.Scope, args: list):
            code_int_ptr = node.left.compile_data.ir_obj
            print("right", node.right.compile_data)
            print("left", node.left.compile_data)
            code_int_val = Compiler._get_ir_variables_from_compiler_variables([node.right.compile_data], s)[0]
            node.compile_data = Compiler.Variable(
                s.builder.store(code_int_val, code_int_ptr),
                s.get_defined_type("int"))

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
                ir.Constant(Compiler.types.bool, value),
                s.get_defined_type("bool"))

     