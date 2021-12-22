import compiler
from seer import Seer
from seer._definitions import Definitions
from llvmlite import ir

class Visitor(compiler.AbstractVisitor):
    build_map = {}
    _encountered_fatal_exception = False

    from seer.procedures._basic import string_, int_, bool_, tag_, var_
    from seer.procedures._shared import default_, unwrap_
    from seer.procedures._var_decl import var_decl_, let_
    from seer.procedures._function_call import function_call_
    from seer.procedures._function import function_, return_
    from seer.procedures._assigns import assigns_
    from seer.procedures._bin_op import bin_op_
    from seer.procedures._if_statement import if_statement_
    from seer.procedures._while_statement import while_statement_

    compiler.visitor(build_map, string_)
    compiler.visitor(build_map, int_)
    compiler.visitor(build_map, bool_)
    
    compiler.visitor(build_map, tag_)
    compiler.visitor(build_map, var_)
    compiler.visitor(build_map, default_)
    compiler.visitor(build_map, unwrap_)
    compiler.visitor(build_map, var_decl_)
    compiler.visitor(build_map, let_)
    compiler.visitor(build_map, function_call_)
    compiler.visitor(build_map, function_)
    compiler.visitor(build_map, return_)
    compiler.visitor(build_map, assigns_)
    compiler.visitor(build_map, bin_op_)
    compiler.visitor(build_map, if_statement_)
    compiler.visitor(build_map, while_statement_)

    @classmethod
    def new_global_context(cls, module) -> compiler.Context:
        return compiler.Context(module, None, cls._generate_new_global_scope(module))

    @classmethod
    def _generate_new_global_scope(cls, module) -> compiler.Scope:
        global_scope = compiler.Scope(parent_scope=None)
        cls._init_primitive_types(global_scope)
        cls._init_special_objs(global_scope, module)

        return global_scope

    @classmethod
    def _init_primitive_types(cls, global_scope : compiler.Scope):
        global_scope.add_type(Seer.Types.Primitives.Int, compiler.IrTypes.int)
        global_scope.add_type(Seer.Types.Primitives.String, None)# TODO: fix
        global_scope.add_type(Seer.Types.Primitives.Float, compiler.IrTypes.float)
        global_scope.add_type(Seer.Types.Primitives.Bool, compiler.IrTypes.bool)

    @classmethod
    def _init_special_objs(cls, global_scope : compiler.Scope, module):
        ir_print_function_type =  ir.FunctionType(ir.IntType(32), [], var_arg=True)
        ir_print_function = ir.Function(
            module, 
            ir_print_function_type, 
            name="printf")
        
        global_scope.add_type(Definitions.print_function_type, ir_print_function_type)
        global_scope.add_obj(
            Definitions.print_function_name,
            compiler.Object(
                ir_print_function, 
                Definitions.print_function_type, 
                Definitions.print_function_name))


    ################################################################################################
    ##
    ## Callback
    ##
    ################################################################################################
    @classmethod
    def exception_callback(cls, exception : compiler.Exceptions.AbstractException):
        cls._encountered_fatal_exception = True
        print(exception.to_str_with_context(cls.text))

    @classmethod
    def init(cls, text):
        cls.text = text
        
    @classmethod
    def finally_handle_exceptions(cls):
        if cls._encountered_fatal_exception:
            print(compiler.Exceptions.delineator, end="")
            msg = (
                "Error: One or more fatal exception were encountered",
                "during \ncompilation. \n\nFix the above errors before re-running your code.\n")
            print(*msg)
            exit(1)
