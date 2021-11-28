from __future__ import annotations
from typing import Tuple
from seer import Seer
from error import Raise
from ast import AstNode
from llvmlite import ir

class Compiler():
    _build_map = {}
    _ir_generation_procedures = []
    _is_init = False

    def __init__(self, asthead : AstNode, txt : str):
        Compiler._init_class()
        self.asthead = asthead
        self.txt = txt
        self.encountered_fatal_exception = False
        self.global_scope = Compiler.Scope()
        self.global_context = Compiler.Context(
            ir.Module(),
            None,
            self.global_scope)

        self._init_primitive_types()
        self._init_special_objs()

    def run(self):
        self._recursive_descent(self.asthead, self.global_context, self)
        if(self.encountered_fatal_exception):
            return ""

        return str(self.global_context.module)

    @classmethod
    def _init_class(cls):
        cls._is_init = True

        cls.ir_generation_procedures = [
            Compiler.int_,
            Compiler.bool_,
            Compiler.string_,
            Compiler.tag_,
            Compiler.var_decl_,
            Compiler.start_,
            Compiler.params_decl_,
            Compiler.var_,
            Compiler.params_,
            Compiler.function_call_,
            Compiler.function_,
            Compiler.codeblock_,
            Compiler.return_,
            Compiler.assigns_,
            Compiler.bin_op_,
            Compiler.let_,
            Compiler.vars_,
            Compiler.var_decl_tuple_,
            Compiler.tuple_,
            Compiler.var_name_tuple_,
            Compiler.if_statement_,
            Compiler.while_statement_
        ]

        cls._build_map = {}
        for proc in cls.ir_generation_procedures:
            if not proc.matches:
                Raise.code_error(f"{proc} requires matches field")
            
            for match in proc.matches:
                cls._build_map[match] = proc

    def _init_primitive_types(self):
        self.global_scope.add_type(Seer.Types.Primitives.Int, Compiler.IrTypes.int)
        self.global_scope.add_type(Seer.Types.Primitives.String, None)# TODO: fix
        self.global_scope.add_type(Seer.Types.Primitives.Float, Compiler.IrTypes.float)
        self.global_scope.add_type(Seer.Types.Primitives.Bool, Compiler.IrTypes.bool)

    def _init_special_objs(self):
        ir_print_function_type =  ir.FunctionType(ir.IntType(32), [], var_arg=True)
        ir_print_function = ir.Function(self.global_context.module, ir_print_function_type, name="printf")
        
        self.global_scope.add_type(Compiler.Definitions.print_function_type, ir_print_function_type)
        self.global_scope.add_obj(
            Compiler.Definitions.print_function_name,
            Compiler.Object(
                ir_print_function, 
                Compiler.Definitions.print_function_type, 
                Compiler.Definitions.print_function_name))
        
        
    @classmethod
    def get_build_procedure(cls, op : str):
        found_proc = cls._build_map.get(op, None)
        if found_proc is None:
            Raise.code_error(f"op {op} is not defined in the build map")
        
        return found_proc
    
    def _print_exception(self, exception : Compiler.Exceptions.AbstractException):
        print(exception.to_str_with_context(self.txt))

    @classmethod
    def _recursive_descent(self, astnode : AstNode, cx : Compiler.Context, callback : Compiler):
        build_procedure : Compiler.IRGenerationProcedure = Compiler.get_build_procedure(astnode.op)
        rdstate = build_procedure.precompile(astnode, cx)

        for child_path in rdstate.get_paths():
            child_cx, child_node = child_path
            self._recursive_descent(child_node, child_cx, callback)

        new_obj = build_procedure.compile(astnode, cx, rdstate.args)
        if isinstance(new_obj, Compiler.Exceptions.AbstractException):
            callback._print_exception(new_obj)
            self.encountered_fatal_exception = True
            exit(0)

        astnode.compile_data = new_obj
     
    @classmethod
    def _get_children_compiler_objects(cls, node : AstNode):
        return [child.compile_data for child in node.vals]

    @classmethod
    def _get_ir_objs(cls, compile_objs : list):
        return [obj[0].get_ir() for obj in compile_objs]
    
    @classmethod
    def _deref_ir_obj_if_needed(cls, compiler_obj : Compiler.Object, cx : Compiler.Context):
        if Compiler.Definitions.is_primitive(compiler_obj.type):
            return cx.builder.load(compiler_obj.get_ir())
        
        return compiler_obj.get_ir()





            


    class IrTypes():
        char = ir.IntType(8)
        bool = ir.IntType(1)
        int = ir.IntType(32)
        float = ir.FloatType()

    class Definitions():
        @classmethod
        def type_equality(cls, typeA : str, typeB : str):
            return typeA == typeB

        reference_type = "#reference"

        @classmethod
        def type_is_reference(cls, type : str):
            return type == Compiler.Definitions.reference_type

        literal_tag = "#"
        def type_is_literal(cls, type : str):
            return (not Compiler.Definitions.type_is_reference(type) 
                and type[0] == Compiler.Definitions.literal_tag)

        print_function_type = "(...) -> (void)"
        print_function_name = "print"

        @classmethod
        def is_primitive(cls, type : str):
            return (Compiler.Definitions.type_equality(type, Seer.Types.Primitives.Int) 
                or Compiler.Definitions.type_equality(type, Seer.Types.Primitives.Float)
                or Compiler.Definitions.type_equality(type, Seer.Types.Primitives.Bool))


    class Exceptions():
        class AbstractException():
            type = None
            description = None

            def __init__(self, msg : str, line_number : int):
                self.msg = msg
                self.line_number = line_number

            def __str__(self):
                return ("================================================================\n"
                    + f"{self.type}Exception\n    (Line {self.line_number}): {self.description}\n"
                    + f"    Info: {self.msg}\n\n")

            def to_str_with_context(self, txt : str):
                str_rep = str(self)

                lines = txt.split('\n')
                index_of_line_number = self.line_number - 1

                start = index_of_line_number - 2
                start = 0 if start < 0 else start

                end = index_of_line_number + 3
                end = len(lines) if end > len(lines) else end

                for i in range(start, end):
                    c = ">>" if i == index_of_line_number else "  "
                    line = f"     {c} {i+1} \t| {lines[i]}\n" 
                    str_rep += line
                    
                return str_rep
        class UseBeforeInitialize(AbstractException):
            type = "UseBeforeInitialize"
            description = "variable cannot be used before it is initialized"

            def __init__(self, msg : str, line_number : int):
                super().__init__(msg, line_number)



            


    class Object():
        def __init__(self, ir_obj, type : str, name="", is_initialized=True):
            self._ir_obj = ir_obj
            self.type = type
            self.name = name
            self.is_initialized = is_initialized

        def is_callable(self):
            return self.is_function()

        def is_function(self):
            return ") -> (" in self.type 

        def is_variable(self):
            return not self.is_function()

        def get_ir(self):
            return self._ir_obj
        
        def get_function_io(self):
            stripstr = lambda x : x.strip()
            params_str, return_str = list(map(stripstr, self.type.split("->")))
            params_str = params_str[1:-1]
            return_str = return_str[1:-1]

            params = list(map(stripstr, params_str.split(",")))
            returns = list(map(stripstr, return_str.split(",")))

            return params, returns

        def matches_type(self, type : str) -> bool:
            return Compiler.Definitions.type_equality(self.type, type)
        

    class Scope():
        def __init__(self, parent_scope : Compiler.Scope = None):
            self._parent_scope = parent_scope
            self._defined_types = {}
            self._defined_objects = {}

        def get_ir_type(self, type : str):
            found_type = self._defined_types.get(type, None)
            if found_type is None and self._parent_scope is not None:
                found_type = self._parent_scope.get_ir_type(type)
            
            if found_type is None:
                Raise.error(f"cannot find type: {type}")
            
            return found_type

        def get_object(self, name : str):
            found_obj = self._defined_objects.get(name, None)
            if found_obj is None and self._parent_scope is not None:
                found_obj = self._parent_scope.get_object(name)

            if found_obj is None:
                Raise.error(f"cannot find obj: {name}")
            
            return found_obj

        def add_obj(self, name : str, compiler_obj):
            if self._defined_objects.get(name, None) is not None:
                Raise.error(f"name {name} is already defined in this scope")

            self._defined_objects[name] = compiler_obj
        
        def add_type(self, type : str, ir_type):
            if self._defined_types.get(type, None) is not None:
                Raise.error(f"type {type} is already defined")
            
            self._defined_types[type] = ir_type


    class Context():
        def __init__(self, module, builder, scope : Compiler.Scope):
            self.module = module
            self.builder = builder
            self.scope = scope

    class RecursiveDescentIntermediateState:
        def __init__(self):
            self._child_paths : list[tuple[Compiler.Context, AstNode]] = []
            self.args = {}

        def add_child(self, cx : Compiler.Context, node : AstNode):
            self._child_paths.append((cx, node))

        def add_arg(self, name : str, val):
            self.args[name] = val

        def get_paths(self) -> list[tuple[Compiler.Context, AstNode]]:
            return self._child_paths


    class IRGenerationProcedure():
        matches = []

        @classmethod
        def precompile(cls, 
            node : AstNode, 
            cx : Compiler.Context
            ) -> Compiler.RecursiveDescentIntermediateState:
            """
            Return a list of child nodes and contexts to use when compiling each child node, as 
            well as a dict of args which will be passed to the compile method.

            Args:
                node (AstNode): Node to precompile
                cx (Compiler.Context): Context to precompile node over.

            Returns:
                [type]: [description]
            """
            rdstate = Compiler.RecursiveDescentIntermediateState()
            for child in node.vals:
                rdstate.add_child(cx, child)

            return rdstate

        @classmethod
        def compile(cls, node : AstNode, cx : Compiler.Context, args : dict) -> list:
            return []
        






    ################################################################################################
    ##
    ## Compiler generation procedures
    ##
    ################################################################################################
 
    class string_(IRGenerationProcedure):
        matches = ["string"]

        @classmethod
        def compile(cls, node: AstNode, cx: Compiler.Context, args: dict) -> list:
            str_data = node.literal_val + "\0"
            c_str_data = ir.Constant(
                ir.ArrayType(Compiler.IrTypes.char, 
                len(str_data)), 
                bytearray(str_data.encode("utf8")))
            
            c_str = cx.builder.alloca(c_str_data.type)
            cx.builder.store(c_str_data, c_str)
            
            return [Compiler.Object(
                c_str,
                Seer.Types.Primitives.String)]

    class int_(IRGenerationProcedure):
        matches = ["int"]

        @classmethod
        def compile(cls, node: AstNode, cx: Compiler.Context, args: dict) -> list:
            return [Compiler.Object(
                ir.Constant(Compiler.IrTypes.int, int(node.literal_val)),
                "#" + Seer.Types.Primitives.Int)]
    
    class bool_(IRGenerationProcedure):
        matches = ["bool"]
        
        @classmethod
        def compile(cls, node: AstNode, cx: Compiler.Context, args: dict) -> list:
            return [Compiler.Object(
                ir.Constant(Compiler.IrTypes.bool, True if node.literal_val == "true" else False),
                "#" + Seer.Types.Primitives.Bool)]

    class tag_(IRGenerationProcedure):
        matches = ["tag"]

        @classmethod
        def compile(cls, node: AstNode, cx: Compiler.Context, args: dict) -> list:
            return [Compiler.Object(
                node.leaf_val,
                Compiler.Definitions.reference_type)]

    class var_decl_(IRGenerationProcedure):
        matches = [":"]

        @classmethod
        def compile(cls, node: AstNode, cx: Compiler.Context, args: dict) -> list:
            child_objs = Compiler._get_children_compiler_objects(node)
            # name and type objs should be #reference type
            compiler_objs_storing_name_tag = child_objs[0]
            compiler_obj_storing_type_tag = child_objs[1][0]
            type = compiler_obj_storing_type_tag.get_ir()
            ir_type = cx.scope.get_ir_type(type)

            new_compiler_objs = []
            for compiler_obj_storing_name in compiler_objs_storing_name_tag:
                name_str = compiler_obj_storing_name.get_ir()
                compiler_obj = Compiler.Object(
                    cx.builder.alloca(ir_type, name=name_str),
                    type,
                    name=name_str)

                cx.scope.add_obj(name_str, compiler_obj)
                new_compiler_objs.append(compiler_obj)

            return new_compiler_objs

    class start_(IRGenerationProcedure):
        matches = ["start"]

    class params_decl_(IRGenerationProcedure):
        matches = ["params_decl"]

    class codeblock_(IRGenerationProcedure):
        matches = ["codeblock"]

    class params_(IRGenerationProcedure):
        matches = ["params"]

        @classmethod
        def compile(cls, node: AstNode, cx: Compiler.Context, args: dict) -> list:
            return [child.compile_data[0] for child in node.vals]

    class var_(IRGenerationProcedure):
        matches = ["var"]

        @classmethod
        def compile(cls, node: AstNode, cx: Compiler.Context, args: dict) -> list:
            name = node.leaf_val
            return [cx.scope.get_object(name)]

    # TODO: fix
    class function_call_(IRGenerationProcedure):
        matches = ["function_call"]

        @classmethod
        def compile(cls, node: AstNode, cx: Compiler.Context, args: dict) -> list:
            compiler_func = node.vals[0].compile_data[0]
            compiler_param_objs = node.vals[1].compile_data
            ir_param_objs = []

            for compiler_obj in compiler_param_objs:
                if not compiler_obj.is_initialized:
                    return Compiler.Exceptions.UseBeforeInitialize(
                        f"variable '{compiler_obj.name}' used here but not initialized",
                        node.line_number)

                ir_param_objs.append(Compiler._deref_ir_obj_if_needed(compiler_obj, cx))

            return Compiler.Object(
                cx.builder.call(compiler_func.get_ir(), ir_param_objs),
                "TODO")

    # TODO: fix
    class function_(IRGenerationProcedure):
        matches = ["function"]

        @classmethod
        def _get_function_decl_names_and_types_int_tuple_form(cls, node : AstNode):
            # params/returns is a tuple of ':' operation nodes. we need to get the leaf_val
            # from the left and right children of each node in params
            params = node.vals[1].vals
            if params and params[0].op == "var_decl_tuple":
                params = params[0].vals

            param_tuples = [(p.vals[0].leaf_val, p.vals[1].leaf_val) for p in params]

            # if no return node is provided
            return_tuples = []

            # if a return node is provided
            if len(node.vals) == 4:
                returns = node.vals[2].vals
                return_tuples = [(r.val[0].leaf_val, r.vals[1].leaf_val) for r in returns]


            return param_tuples, return_tuples

        @classmethod
        def _get_function_type(cls, node : AstNode, cx : Compiler.Context):
            param_tuples, return_tuples = cls._get_function_decl_names_and_types_int_tuple_form(node)
            
            param_types = [x[1] for x in param_tuples]
            return_types = [x[1] for x in return_tuples]

            function_ir_types = []
            function_ir_types += [cx.scope.get_ir_type(type) for type in param_types]
            function_ir_types += [cx.scope.get_ir_type(type) for type in return_types]

            ir_type = ir.FunctionType(ir.VoidType(), function_ir_types)

            return f"({','.join(param_types)}) -> ({','.join(return_types)})", ir_type

        @classmethod
        def _get_function_name(cls, node : AstNode, cx : Compiler.Context):
            return node.vals[0].leaf_val

        @classmethod
        def _add_parameters_to_new_context(cls, node : AstNode, cx : Compiler.Context, func):
            param_tuples, return_tuples = cls._get_function_decl_names_and_types_int_tuple_form(node)

            for i, param_tuple in enumerate(param_tuples):
                name, type = param_tuple
                ir_obj = cx.builder.alloca(cx.scope.get_ir_type(type), name=name)
                compiler_obj = Compiler.Object(
                    ir_obj,
                    type,
                    name=name)
                cx.scope.add_obj(name, compiler_obj)
                cx.builder.store(func.args[i], ir_obj)

            for name, type in return_tuples:
                cx.builder.alloca(cx.scope.get_ir_type(type), name=name)
                compiler_obj = Compiler.Object(
                    ir_obj,
                    type,
                    name=name)
                cx.scope.add_obj(name, compiler_obj)

        @classmethod
        def precompile(cls, node: AstNode, cx: Compiler.Context):
            name = cls._get_function_name(node, cx)

            # TODO: impl
            func_name = cls._get_function_name(node, cx)
            func_type, ir_type = cls._get_function_type(node, cx)
            # TODO: figure out how to get parameter names
            func = ir.Function(cx.module, ir_type, name=func_name)

            compiler_obj = Compiler.Object(
                func,
                func_type,
                name=func_name)

            cx.scope.add_obj(func_name, compiler_obj)

            builder = ir.IRBuilder(func.append_basic_block("entry"))
            new_context = Compiler.Context(cx.module, builder, Compiler.Scope(parent_scope=cx.scope))
            cls._add_parameters_to_new_context(node, new_context, func)

            rdstate = Compiler.RecursiveDescentIntermediateState()
            rdstate.add_arg("function", compiler_obj)
            rdstate.add_arg("new_cx", new_context)
            rdstate.add_child(new_context, node.vals[-1])

            return rdstate
        
        @classmethod
        def compile(cls, node: AstNode, cx: Compiler.Context, args: dict) -> list:
            new_cx = args["new_cx"]
            if(not new_cx.builder.block.is_terminated):
                new_cx.builder.ret_void()
            return [args["function"]]



    class return_(IRGenerationProcedure):
        matches = ["return"]

        @classmethod
        def compile(cls, node: AstNode, cx: Compiler.Context, args: dict) -> list:
            cx.builder.ret_void()
            return []

    class assigns_(IRGenerationProcedure):
        matches = ["="]

        @classmethod
        def _single_assign(cls, left_compiler_obj, right_compiler_obj, cx : Compiler.Context):
            ir_obj_to_assign = Compiler._deref_ir_obj_if_needed(right_compiler_obj, cx)
            left_compiler_obj.is_initialized=True
            return Compiler.Object(
                cx.builder.store(ir_obj_to_assign, left_compiler_obj.get_ir()),
                left_compiler_obj.type)

        @classmethod
        def compile(cls, node: AstNode, cx: Compiler.Context, args: dict) -> list:
            left_compiler_objs = node.left.compile_data
            right_compiler_objs = node.right.compile_data

            if len(left_compiler_objs) != len(right_compiler_objs):
                Raise.error(f"expected equal sized tuples during unpacking")
            
            compiler_objs = []
            for left_compiler_obj, right_compiler_obj in zip(left_compiler_objs, right_compiler_objs):
                compiler_objs.append(cls._single_assign(left_compiler_obj, right_compiler_obj, cx))

            return compiler_objs


            
    class bin_op_(IRGenerationProcedure):
        matches = [
            "+", "-", "/", "*",
            "<", ">", "<=", ">=",
            "==", "!=",
            "+=", "-=", "/=", "*="
        ]

        @classmethod
        def compile(cls, node: AstNode, cx: Compiler.Context, args: dict) -> list:
            op = node.op
            ir_obj = None

            left_compiler_obj = node.left.compile_data[0]
            right_compiler_obj = node.right.compile_data[0]

            builder_function_params = [
                Compiler._deref_ir_obj_if_needed(left_compiler_obj, cx),
                Compiler._deref_ir_obj_if_needed(right_compiler_obj, cx)
            ]

            if not left_compiler_obj.is_initialized:
                return Compiler.Exceptions.UseBeforeInitialize(
                    f"variable '{left_compiler_obj.name}' used here but not initialized",
                    node.line_number) 

            if not right_compiler_obj.is_initialized:
                return Compiler.Exceptions.UseBeforeInitialize(
                    f"variable '{right_compiler_obj.name}' used here but not initialized",
                    node.line_number)

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

                new_compiler_obj = Compiler.Object(
                    ir_obj,
                    "#" + left_compiler_obj.type)
                    
                return Compiler.assigns_._single_assign(left_compiler_obj, new_compiler_obj, cx)



            elif(op == "<" 
                or op == ">"
                or op == ">="
                or op == "<="
                or op == "=="
                or op == "!="):
                ir_obj = cx.builder.icmp_signed(op, *builder_function_params)
                return [Compiler.Object(
                    ir_obj,
                    Seer.Types.Primitives.Bool)]
                
            else:
                Raise.code_error(f"op ({op}) is not implemented") 

            return [Compiler.Object(
                ir_obj,
                "#" + left_compiler_obj.type)]

    class let_(IRGenerationProcedure):
        matches = ["let"]

        @classmethod
        def compile(cls, node: AstNode, cx: Compiler.Context, args: dict) -> list:
            compiler_objs = Compiler.var_decl_.compile(node, cx, args)
            for obj in compiler_objs:
                obj.is_initialized = False

            return compiler_objs

    class vars_(IRGenerationProcedure):
        matches = ["vars"]

        @classmethod
        def compile(cls, node: AstNode, cx: Compiler.Context, args: dict) -> list:
            return [child.compile_data[0] for child in node.vals]

    class var_decl_tuple_(IRGenerationProcedure):
        matches = ["var_decl_tuple"]

        @classmethod
        def compile(cls, node: AstNode, cx: Compiler.Context, args: dict) -> list:
            return [child.compile_data[0] for child in node.vals]

    class tuple_(IRGenerationProcedure):
        matches = ["tuple"]

        @classmethod
        def compile(cls, node: AstNode, cx: Compiler.Context, args: dict) -> list:
            return [child.compile_data[0] for child in node.vals]

    class var_name_tuple_(IRGenerationProcedure):
        matches = ["var_name_tuple"]

        @classmethod
        def compile(cls, node: AstNode, cx: Compiler.Context, args: dict) -> list:
            return [child.compile_data[0] for child in node.vals]
            
    class if_statement_(IRGenerationProcedure):
        matches = ["if_statement"]

        @classmethod
        def precompile(cls, node: AstNode, cx: Compiler.Context):
            rdstate = Compiler.RecursiveDescentIntermediateState()
            new_blocks = [cx.builder.block]
            new_contexts = [cx]

            # first child is an if-statement clause which lives in the original block
            rdstate.add_child(cx, node.vals[0])

            for child in node.vals[1:]:
                new_block = cx.builder.append_basic_block()
                new_blocks.append(new_block)

                new_cx = Compiler.Context(
                    cx.module, 
                    ir.IRBuilder(block=new_block),
                    Compiler.Scope(parent_scope=cx.scope))

                new_contexts.append(new_cx)
                rdstate.add_child(new_cx, child)
            
            new_blocks.append(cx.builder.append_basic_block())

            rdstate.add_arg("blocks", new_blocks)
            rdstate.add_arg("contexts", new_contexts)

            return rdstate
        
        @classmethod
        def compile(cls, node: AstNode, cx: Compiler.Context, args: dict) -> list:
            n = len(node.vals)
            blocks = args["blocks"]
            contexts = args["contexts"]

            i = 0
            while i + 1 < n:
                statement_cx = contexts[i]
                codeblock_block = blocks[i+1]
                next_statement_block = blocks[i+2]

                statement_compiler_obj = node.vals[i].compile_data[0]

                statement_cx.builder.cbranch(
                    statement_compiler_obj.get_ir(),
                    codeblock_block,
                    next_statement_block)

                i += 2

            # handle the case of hanging 'else' statement
            if n % 2 == 1:
                else_cx = contexts[-1]
                else_cx.builder.branch(blocks[-1])

            
            # connect all codeblock_blocks to the final codeblock
            i = 1
            while i < n:
                codeblock_cx = contexts[i]

                # last block is the block added after the if complex
                codeblock_cx.builder.branch(blocks[-1])
                i += 2

            cx.builder.position_at_start(blocks[-1])

            return []

    class while_statement_(IRGenerationProcedure):
        matches = ["while_statement"]

        @classmethod
        def precompile(cls, node: AstNode, cx: Compiler.Context) -> Compiler.RecursiveDescentIntermediateState:
            rdstate = Compiler.RecursiveDescentIntermediateState()

            statement_block = cx.builder.append_basic_block()
            statement_cx = Compiler.Context(
                cx.module,
                ir.IRBuilder(block=statement_block),
                Compiler.Scope(parent_scope=cx.scope))

            body_block = cx.builder.append_basic_block()
            body_cx = Compiler.Context(
                cx.module,
                ir.IRBuilder(block=body_block),
                Compiler.Scope(parent_scope=cx.scope))

            after_block = cx.builder.append_basic_block()

            rdstate.add_child(statement_cx, node.vals[0])
            rdstate.add_child(body_cx, node.vals[1])

            rdstate.add_arg("statement_block", statement_block)
            rdstate.add_arg("statement_cx", statement_cx)
            rdstate.add_arg("body_block", body_block)
            rdstate.add_arg("body_cx", body_cx)
            rdstate.add_arg("after_block", after_block)

            return rdstate

        @classmethod
        def compile(cls, node: AstNode, cx: Compiler.Context, args: dict) -> list:
            statement_block = args["statement_block"]
            statement_cx = args["statement_cx"]
            body_block = args["body_block"]
            body_cx = args["body_cx"]
            after_block = args["after_block"]

            statement_compiler_obj = node.vals[0].compile_data[0]

            statement_cx.builder.cbranch(
                    statement_compiler_obj.get_ir(),
                    body_block,
                    after_block)

            body_cx.builder.branch(statement_block)
            cx.builder.branch(statement_block)
            cx.builder.position_at_start(after_block)
            