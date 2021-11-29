from __future__ import annotations
from typing import List, Tuple
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


    def run(self):
        callback = Compiler.Callback(txt=self.txt)
        options = Compiler.Options(should_not_emit_ir=True)
        module = ir.Module()
        global_context = self._generate_new_global_context(module)
        self._recursive_descent(self.asthead, global_context, callback, options)
        if(callback.encountered_fatal_exception()):
            print(Compiler.Exceptions.delineator, end="")
            msg = (
                "Error: One or more fatal exception were encountered",
                "during \ncompilation. \n\nFix the above errors before re-running your code.\n")
            print(*msg)
            exit(1)

        callback = Compiler.Callback(txt=self.txt)
        options = Compiler.Options(should_not_emit_ir=False)
        module = ir.Module()
        global_context = self._generate_new_global_context(module)
        self._recursive_descent(self.asthead, global_context, callback, options)

        return str(module)


    @classmethod
    def _init_class(cls):
        if cls._is_init:
            return

        cls._is_init = True

        cls.ir_generation_procedures = [
            Compiler.default_,
            Compiler.unwrap_,
            Compiler.int_,
            Compiler.bool_,
            Compiler.string_,
            Compiler.tag_,
            Compiler.var_decl_,
            Compiler.var_,
            Compiler.function_call_,
            Compiler.function_,
            Compiler.return_,
            Compiler.assigns_,
            Compiler.bin_op_,
            Compiler.let_,
            Compiler.if_statement_,
            Compiler.while_statement_
        ]

        cls._build_map = {}
        for proc in cls.ir_generation_procedures:
            if not proc.matches:
                Raise.code_error(f"{proc} requires matches field")
            
            for match in proc.matches:
                cls._build_map[match] = proc
    

    @classmethod
    def _generate_new_global_context(cls, module) -> Compiler.Context:
        return Compiler.Context(module, None, cls._generate_new_global_scope(module))


    @classmethod
    def _generate_new_global_scope(cls, module) -> Compiler.Scope:
        global_scope = Compiler.Scope(parent_scope=None)
        Compiler._init_primitive_types(global_scope)
        Compiler._init_special_objs(global_scope, module)

        return global_scope


    @classmethod
    def _init_primitive_types(cls, global_scope : Compiler.Scope):
        global_scope.add_type(Seer.Types.Primitives.Int, Compiler.IrTypes.int)
        global_scope.add_type(Seer.Types.Primitives.String, None)# TODO: fix
        global_scope.add_type(Seer.Types.Primitives.Float, Compiler.IrTypes.float)
        global_scope.add_type(Seer.Types.Primitives.Bool, Compiler.IrTypes.bool)


    @classmethod
    def _init_special_objs(cls, global_scope : Compiler.Scope, module):
        ir_print_function_type =  ir.FunctionType(ir.IntType(32), [], var_arg=True)
        ir_print_function = ir.Function(
            module, 
            ir_print_function_type, 
            name="printf")
        
        global_scope.add_type(Compiler.Definitions.print_function_type, ir_print_function_type)
        global_scope.add_obj(
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


    @classmethod
    def _recursive_descent(self, 
            astnode : AstNode, 
            cx : Compiler.Context, 
            callback : Compiler.Callback,
            options : Compiler.Options) -> None:

        # start
        build_procedure : Compiler.IRGenerationProcedure = Compiler.get_build_procedure(astnode.op)
        rdstate = build_procedure.precompile(astnode, cx, options)

        for child_path in rdstate.get_paths():
            child_cx, child_node = child_path
            self._recursive_descent(child_node, child_cx, callback, options)

        new_objs = build_procedure.compile(astnode, cx, rdstate.args, options)

        if any(map(lambda obj: isinstance(obj, Compiler.Exceptions.AbstractException), new_objs)):
            amended_objs = []
            for obj in new_objs:
                if isinstance(obj, Compiler.Exceptions.AbstractException):
                    callback._print_exception(obj)
                    callback.notify_of_fatal_exception()
                    amended_objs.append(obj.get_stub())
                else:
                    amended_objs.append(obj)
            
            new_objs = amended_objs

        astnode.compile_data = new_objs
     

    @classmethod
    def _get_children_compiler_objects(cls, node : AstNode):
        return [child.compile_data for child in node.vals]
    

    @classmethod
    def _deref_ir_obj_if_needed(cls, compiler_obj : Compiler.Object, cx : Compiler.Context):
        if Compiler.Definitions.is_primitive(compiler_obj.type):
            return cx.builder.load(compiler_obj.get_ir())
        
        return compiler_obj.get_ir()








    ################################################################################################
    ##
    ## Definitions 
    ##
    ################################################################################################
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

    class IrTypes():
        char = ir.IntType(8)
        bool = ir.IntType(1)
        int = ir.IntType(32)
        float = ir.FloatType()



    ################################################################################################
    ##
    ## Exceptions
    ##
    ################################################################################################
    class Exceptions():
        delineator = "================================================================\n"

        class AbstractException():
            type = None
            description = None

            def __init__(self, msg : str, line_number : int):
                self.msg = msg
                self.line_number = line_number

            def __str__(self):
                padding = " "*len(str(self.line_number))
                return (Compiler.Exceptions.delineator
                    + f"{self.type}Exception\n    Line {self.line_number}: {self.description}\n"
                    + f"{padding}     INFO: {self.msg}\n\n")

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

            def set_compiler_stub(self, stub : Compiler.Stub):
                self._stub = stub

            def get_stub(self) -> Compiler.Stub:
                return self._stub
        
        class UseBeforeInitialize(AbstractException):
            type = "UseBeforeInitialize"
            description = "variable cannot be used before it is initialized"

            def __init__(self, msg : str, line_number : int):
                super().__init__(msg, line_number)
        
        class UndefinedVariable(AbstractException):
            type = "UndefinedVariable"
            description = "variable is not defined"
        
            def __init__(self, msg: str, line_number: int):
                super().__init__(msg, line_number)





            
    ################################################################################################
    ##
    ## Architecture
    ##
    ################################################################################################

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

        def get_tag_value(self):
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

    class Stub(Object):
        def __init__(self, type : str, name="", is_initialized=True):
            self._tag_value = None
            super().__init__(None, type, name, is_initialized)

        def set_tag_value(self, val : str):
            self._tag_value = val 

        def get_tag_value(self):
            return self._tag_value

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
                return Compiler.Exceptions.UndefinedVariable(
                    f"variable '{name}' is not defined", 
                    0)
            
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

    class Options():
        """
        Used to supply additional parameters to IRGenerationProcedure(s) without having to modify
        the precompile/compile signatures
        """

        def __init__(self, should_not_emit_ir : bool=False):
            self.should_not_emit_ir = should_not_emit_ir

    class RecursiveDescentIntermediateState():
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
                cx : Compiler.Context,
                options : Compiler.Options=None
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
        def compile(cls, 
                node : AstNode, 
                cx : Compiler.Context, 
                args : dict, 
                options : Compiler.Options=None) -> list[Compiler.Object]:
            # start
            return []
        
    class Callback():
        def __init__(self, txt : str):
            self.txt = txt
            self._encountered_fatal_exception = False

        def notify_of_fatal_exception(self):
            self._encountered_fatal_exception = True

        def encountered_fatal_exception(self):
            return self._encountered_fatal_exception

        def _print_exception(self, exception : Compiler.Exceptions.AbstractException):
            print(exception.to_str_with_context(self.txt))






    ################################################################################################
    ##
    ## Compiler generation procedures
    ##
    ################################################################################################
 
    class string_(IRGenerationProcedure):
        matches = ["string"]

        @classmethod
        def compile(cls, 
                node : AstNode, 
                cx : Compiler.Context, 
                args : dict, 
                options : Compiler.Options = None) -> list[Compiler.Object]:

            # validation
            cobj_type = Seer.Types.Primitives.String
            if options.should_not_emit_ir:
                return [Compiler.Stub(cobj_type)]

            # generation 
            str_data = node.literal_val + "\0"
            c_str_data = ir.Constant(
                ir.ArrayType(Compiler.IrTypes.char, 
                len(str_data)), 
                bytearray(str_data.encode("utf8")))
            
            c_str = cx.builder.alloca(c_str_data.type)
            cx.builder.store(c_str_data, c_str)
            
            return [Compiler.Object(
                c_str,
                cobj_type)]

    class int_(IRGenerationProcedure):
        matches = ["int"]

        @classmethod
        def compile(cls, 
                node : AstNode, 
                cx : Compiler.Context, 
                args : dict, 
                options : Compiler.Options = None) -> list[Compiler.Object]:

            # validation
            cobj_type = "#" + Seer.Types.Primitives.Int
            if options.should_not_emit_ir:
                return [Compiler.Stub(cobj_type)]

            # generation
            return [Compiler.Object(
                ir.Constant(Compiler.IrTypes.int, int(node.literal_val)),
                cobj_type)]
    
    class bool_(IRGenerationProcedure):
        matches = ["bool"]
        
        @classmethod
        def compile(cls, 
                node : AstNode, 
                cx : Compiler.Context, 
                args : dict, 
                options : Compiler.Options = None) -> list[Compiler.Object]:

            # validation
            cobj_type = "#" + Seer.Types.Primitives.Bool
            if options.should_not_emit_ir:
                return [Compiler.Stub(cobj_type)]

            # generation
            return [Compiler.Object(
                ir.Constant(Compiler.IrTypes.bool, True if node.literal_val == "true" else False),
                cobj_type)]

    class tag_(IRGenerationProcedure):
        matches = ["tag"]

        @classmethod
        def compile(cls, 
                node : AstNode, 
                cx : Compiler.Context, 
                args : dict, 
                options : Compiler.Options = None) -> list[Compiler.Object]:

            # validation
            cobj_type = Compiler.Definitions.reference_type
            if options.should_not_emit_ir:
                stub_obj = Compiler.Stub(cobj_type)
                stub_obj.set_tag_value(node.leaf_val)

                return [stub_obj]
            
            # generation
            return [Compiler.Object(
                node.leaf_val,
                cobj_type)]

    class var_decl_(IRGenerationProcedure):
        matches = [":"]

        @classmethod
        def compile(cls, 
                node : AstNode, 
                cx : Compiler.Context, 
                args : dict, 
                options : Compiler.Options = None) -> list[Compiler.Object]:

            # shared
            child_objs = Compiler._get_children_compiler_objects(node)
            compiler_obj_storing_type_tag = child_objs[1][0]
            cobj_type = compiler_obj_storing_type_tag.get_tag_value()

            # name and type objs should be #reference type
            compiler_objs_storing_name_tag = child_objs[0]
            ir_type = cx.scope.get_ir_type(cobj_type)
            new_compiler_objs = []
            for compiler_obj_storing_name in compiler_objs_storing_name_tag:
                name_str = compiler_obj_storing_name.get_tag_value()

                compiler_obj = None
                if options.should_not_emit_ir:
                    # validation
                    compiler_obj = Compiler.Stub(cobj_type, name=name_str)
                else:
                    # generation
                    compiler_obj = Compiler.Object(
                        cx.builder.alloca(ir_type, name=name_str),
                        cobj_type,
                        name=name_str)

                cx.scope.add_obj(name_str, compiler_obj)
                new_compiler_objs.append(compiler_obj)

            return new_compiler_objs

    class default_(IRGenerationProcedure):
        matches = ["start", "params_decl", "codeblock"]

    class unwrap_(IRGenerationProcedure):
        matches = ["params", "vars", "tuple", "var_decl_tuple", "var_name_tuple"]

        @classmethod
        def compile(cls, 
                node : AstNode, 
                cx : Compiler.Context, 
                args : dict, 
                options : Compiler.Options = None) -> list[Compiler.Object]:
            # start
            return [child.compile_data[0] for child in node.vals]

    class var_(IRGenerationProcedure):
        matches = ["var"]

        @classmethod
        def compile(cls, 
                node : AstNode, 
                cx : Compiler.Context, 
                args : dict, 
                options : Compiler.Options = None) -> list[Compiler.Object]:
                
            # start
            name = node.leaf_val
            compiler_obj = cx.scope.get_object(name)

            # set line_number if exception because 'get_object' method does not have access to it
            if isinstance(compiler_obj, Compiler.Exceptions.AbstractException):
                exception = compiler_obj
                exception.line_number = node.line_number
                exception.set_compiler_stub(Compiler.Stub("???", name=name))

            return [compiler_obj]

    # TODO: fix
    class function_call_(IRGenerationProcedure):
        matches = ["function_call"]

        @classmethod
        def compile(cls, 
                node : AstNode, 
                cx : Compiler.Context, 
                args : dict, 
                options : Compiler.Options = None) -> list[Compiler.Object]:

            # start
            compiler_func = node.vals[0].compile_data[0]
            compiler_param_objs = node.vals[1].compile_data
            ir_param_objs = []

            for compiler_obj in compiler_param_objs:
                if not compiler_obj.is_initialized:
                    return Compiler.Exceptions.UseBeforeInitialize(
                        f"variable '{compiler_obj.name}' used here but not initialized",
                        node.line_number)

                if options.should_not_emit_ir:
                    # do nothing
                    None
                else:
                    ir_param_objs.append(Compiler._deref_ir_obj_if_needed(compiler_obj, cx))
        
            # validation
            cobj_type = "TODO"
            if options.should_not_emit_ir:
                return [Compiler.Stub(cobj_type)]

            # generation
            return [Compiler.Object(
                cx.builder.call(compiler_func.get_ir(), ir_param_objs),
                cobj_type)]

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
            param_tuples, return_tuples = \
                cls._get_function_decl_names_and_types_int_tuple_form(node)
            
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
            param_tuples, return_tuples = \
                cls._get_function_decl_names_and_types_int_tuple_form(node)

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
        def precompile(cls, 
                node : AstNode, 
                cx : Compiler.Context,
                options : Compiler.Options=None
                ) -> Compiler.RecursiveDescentIntermediateState:

            # start
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
            new_context = Compiler.Context(
                cx.module, 
                builder, 
                Compiler.Scope(parent_scope=cx.scope))

            cls._add_parameters_to_new_context(node, new_context, func)

            rdstate = Compiler.RecursiveDescentIntermediateState()
            rdstate.add_arg("function", compiler_obj)
            rdstate.add_arg("new_cx", new_context)
            rdstate.add_child(new_context, node.vals[-1])

            return rdstate
        
        @classmethod
        def compile(cls, 
                node : AstNode, 
                cx : Compiler.Context, 
                args : dict, 
                options : Compiler.Options = None) -> list[Compiler.Object]:
            # start
            new_cx = args["new_cx"]
            if(not new_cx.builder.block.is_terminated):
                new_cx.builder.ret_void()
            return [args["function"]]

    class return_(IRGenerationProcedure):
        matches = ["return"]

        @classmethod
        def compile(cls, 
                node : AstNode, 
                cx : Compiler.Context, 
                args : dict, 
                options : Compiler.Options = None) -> list[Compiler.Object]:
            
            # validation
            if options.should_not_emit_ir:
                return []

            # generation
            cx.builder.ret_void()
            return []

    class assigns_(IRGenerationProcedure):
        matches = ["="]

        @classmethod
        def _single_assign(cls, 
                left_compiler_obj, 
                right_compiler_obj, 
                cx : Compiler.Context, 
                options : Compiler.Options):
                
            # start
            ir_obj_to_assign = Compiler._deref_ir_obj_if_needed(right_compiler_obj, cx)
            left_compiler_obj.is_initialized=True

            # validation
            cobj_type = "TODO"
            if options.should_not_emit_ir:
                return Compiler.Stub(left_compiler_obj.type)

            return Compiler.Object(
                cx.builder.store(ir_obj_to_assign, left_compiler_obj.get_ir()),
                left_compiler_obj.type)

        @classmethod
        def compile(cls, 
                node : AstNode, 
                cx : Compiler.Context, 
                args : dict, 
                options : Compiler.Options = None) -> list[Compiler.Object]:

            # start
            left_compiler_objs = node.left.compile_data
            right_compiler_objs = node.right.compile_data

            if len(left_compiler_objs) != len(right_compiler_objs):
                Raise.error(f"expected equal sized tuples during unpacking")
            
            compiler_objs = []
            for left_compiler_obj, right_compiler_obj in zip(left_compiler_objs, right_compiler_objs):
                compiler_objs.append(
                    cls._single_assign(
                    left_compiler_obj, 
                    right_compiler_obj, 
                    cx, 
                    options))

            return compiler_objs

    class bin_op_(IRGenerationProcedure):
        matches = [
            "+", "-", "/", "*",
            "<", ">", "<=", ">=",
            "==", "!=",
            "+=", "-=", "/=", "*="
        ]

        @classmethod
        def compile(cls, 
                node : AstNode, 
                cx : Compiler.Context, 
                args : dict, 
                options : Compiler.Options = None) -> list[Compiler.Object]:

            # start
            op = node.op
            ir_obj = None

            left_compiler_obj = node.left.compile_data[0]
            right_compiler_obj = node.right.compile_data[0]

            exception_msg = ""
            if not left_compiler_obj.is_initialized:
                exception_msg += f"variable '{left_compiler_obj.name}'"

            if not right_compiler_obj.is_initialized:
                if exception_msg:
                    exception_msg += " and "
                
                exception_msg += f"variable '{right_compiler_obj.name}'"

            if exception_msg:
                exception = Compiler.Exceptions.UseBeforeInitialize(
                    f"{exception_msg} used here but not initialized",
                    node.line_number)

                exception.set_compiler_stub(Compiler.Stub(left_compiler_obj.type))
                return [exception]

            # validation
            cobj_type = "TODO"
            if options.should_not_emit_ir:
                if   ( op == "+" 
                    or op == "-" 
                    or op == "*" 
                    or op == "/" 
                    or op == "+="
                    or op == "-="
                    or op == "/="
                    or op == "*="):

                    return [Compiler.Stub(left_compiler_obj.type)]

                elif   ( op == "=="
                    or op == "<="
                    or op == ">="
                    or op == "<"
                    or op == ">"
                    or op == "!="):

                    return [Compiler.Stub("#" + Seer.Types.Primitives.Bool)]
                

            builder_function_params = [
                Compiler._deref_ir_obj_if_needed(left_compiler_obj, cx),
                Compiler._deref_ir_obj_if_needed(right_compiler_obj, cx)
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
                    "#" + Seer.Types.Primitives.Bool)]
                
            else:
                Raise.code_error(f"op ({op}) is not implemented") 

            return [Compiler.Object(
                ir_obj,
                "#" + left_compiler_obj.type)]

    class let_(IRGenerationProcedure):
        matches = ["let"]

        @classmethod
        def compile(cls, 
                node : AstNode, 
                cx : Compiler.Context, 
                args : dict, 
                options : Compiler.Options = None) -> list[Compiler.Object]:
            # start
            compiler_objs = Compiler.var_decl_.compile(node, cx, args, options)
            for obj in compiler_objs:
                obj.is_initialized = False

            return compiler_objs
            
    class if_statement_(IRGenerationProcedure):
        matches = ["if_statement"]

        @classmethod
        def precompile(cls, 
                node : AstNode, 
                cx : Compiler.Context,
                options : Compiler.Options=None
                ) -> Compiler.RecursiveDescentIntermediateState:
                
            # start
            rdstate = Compiler.RecursiveDescentIntermediateState()
            new_blocks = [cx.builder.block]
            new_contexts = [cx]

            # first child is an if-statement clause which lives in the original block
            rdstate.add_child(cx, node.vals[0])

            for child in node.vals[1:]:
                if options.should_not_emit_ir:
                    new_cx = Compiler.Context(cx.module, None, Compiler.Scope(parent_scope=cx.scope))
                    rdstate.add_child(new_cx, child)
                    continue

                new_block = cx.builder.append_basic_block()
                new_blocks.append(new_block)

                new_cx = Compiler.Context(
                    cx.module, 
                    ir.IRBuilder(block=new_block),
                    Compiler.Scope(parent_scope=cx.scope))

                new_contexts.append(new_cx)
                rdstate.add_child(new_cx, child)

            if options.should_not_emit_ir:
                return rdstate 

            new_blocks.append(cx.builder.append_basic_block())

            rdstate.add_arg("blocks", new_blocks)
            rdstate.add_arg("contexts", new_contexts)

            return rdstate
        
        @classmethod
        def compile(cls, 
                node : AstNode, 
                cx : Compiler.Context, 
                args : dict, 
                options : Compiler.Options = None) -> list[Compiler.Object]:

            # validation
            if options.should_not_emit_ir:
                return []

            # start
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
                    Compiler._deref_ir_obj_if_needed(statement_compiler_obj, cx),
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
        def precompile(cls, 
                node : AstNode, 
                cx : Compiler.Context,
                options : Compiler.Options=None
                ) -> Compiler.RecursiveDescentIntermediateState:

            # start
            rdstate = Compiler.RecursiveDescentIntermediateState()

            # validation
            if options.should_not_emit_ir:
                statement_cx = Compiler.Context(cx.module, None, Compiler.Scope(parent_scope=cx.scope))
                rdstate.add_child(statement_cx, node.vals[0])                

                body_cx = Compiler.Context(cx.module, None, Compiler.Scope(parent_scope=cx.scope))
                rdstate.add_child(body_cx, node.vals[1])

                return rdstate

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
        def compile(cls, 
                node : AstNode, 
                cx : Compiler.Context, 
                args : dict, 
                options : Compiler.Options = None) -> list[Compiler.Object]:

            # validation
            if options.should_not_emit_ir:
                return []

            # start
            statement_block = args["statement_block"]
            statement_cx = args["statement_cx"]
            body_block = args["body_block"]
            body_cx = args["body_cx"]
            after_block = args["after_block"]

            statement_compiler_obj = node.vals[0].compile_data[0]
            statement_cx.builder.cbranch(
                    Compiler._deref_ir_obj_if_needed(statement_compiler_obj, cx),
                    body_block,
                    after_block)

            body_cx.builder.branch(statement_block)
            cx.builder.branch(statement_block)
            cx.builder.position_at_start(after_block)

            return []
            