from __future__ import annotations

from alpaca.asts import CLRList, CLRToken
from alpaca.config import Config
from alpaca.validator import Indexer, Validator, AbstractModule, AbstractType, AbstractObject, AbstractException
from alpaca.utils import AbstractFlags 

from seer._listir import ListIRParser

from error import Raise

class Object(AbstractObject):
    def __init__(self, 
            name : str, 
            type : Type, 
            mod: AbstractModule,
            is_let : bool = False, 
            is_mut : bool = False, 
            is_const : bool = False,
            is_ret : bool = False,
            is_arg : bool = False,
            is_ptr: bool = False,
            is_val: bool = False,
            is_var: bool = False,
            is_safe_ptr: bool = False, 
            ):

        self.name = name
        self.type = type
        self.mod = mod
        self.is_let = is_let
        self.is_mut = is_mut
        self.is_const = is_const
        self.is_ret = is_ret
        self.is_arg = is_arg
        self.is_ptr = is_ptr
        self.is_val = is_val
        self.is_var = is_var
        self.is_safe_ptr = is_safe_ptr

    def __str__(self) -> str:
        return f"{self.name}<{self.type.cannonical_name()}>"

class Exceptions():
    class MemoryTypeMismatch(AbstractException):
        type = "MemoryTypeMismatch"
        description = "cannot assign due to let/var/val differences"

        def __init__(self, msg : str, line_number : int):
            super().__init__(msg, line_number)

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

    class RedefinedIdentifier(AbstractException):
        type = "RedefinedIdentifier"
        description = "identifier is already in use"
        
        def __init__(self, msg : str, line_number : int):
            super().__init__(msg, line_number)

    class TypeMismatch(AbstractException):
        type = "TypeMismatch"
        description = "type different from expected"

        def __init__(self, msg : str, line_number : int):
            super().__init__(msg, line_number)

    class TupleSizeMismatch(AbstractException):
        type = "TupleSizeMismatch"
        description = "tuple unpack requires equal sizes"

        def __init__(self, msg : str, line_number : int):
            super().__init__(msg, line_number)

class Type(AbstractType):
    classifications = ["function", "product", "named_product", "or", "base"]
    base_type_name = "base"
    function_type_name = "function"
    product_type_name = "product"
    or_type_name = "or"
    named_product_type_name = "named_product"

    def __init__(self, type=None):
        self._name = None
        self.classification = type
        self.mod = None
        self.components: list[Type] = []
        self.component_names : list[str] = []
        self.arg: Type = None
        self.ret: Type = None
        self.nullable = False
        self.is_ptr = False

    def name(self):
        if self._name is not None:
            return self._name
        return self.cannonical_name()

    def get_member_attribute_named(self, name: str):
        if self.classification != AbstractType.struct_classification:
            raise Exception(f"can only get member attribute of structs; got {self.classification} instead")
        idx = self.component_names.index(name)
        return self.components[idx]

    def cannonical_name(self) -> str:
        if self.classification == AbstractType.base_classification:
            return self._name
        elif self.classification == AbstractType.tuple_classification:
            component_type_strs = [x.cannonical_name() for x in self.components]
            return f"({', '.join(component_type_strs)})"
        elif self.classification == AbstractType.struct_classification:
            component_type_strs = [x.cannonical_name() for x in self.components]
            component_key_value_strs = [f"{name}:{type}" 
                for name, type in zip(self.component_names, component_type_strs)]
            return f"({', '.join(component_key_value_strs)})"
        elif self.classification == AbstractType.function_classification:
            args_names = self.arg.cannonical_name() if self.arg is not None else ""
            rets_names = self.ret.cannonical_name() if self.ret is not None else "void"
            return f"({args_names}) -> {rets_names}"
        else:
            Raise.error("cannoncial_name not implemented")

    def __str__(self):
        if self._name is not None:
            return f"{self._name}<{self.cannonical_name()}>"
        return self.name()
            
    @classmethod
    def new_base_type(cls, name: str, nullable=False, is_ptr=False) -> Type:
        type = Type(AbstractType.base_classification)
        type._name = name
        type.nullable = nullable
        type.is_ptr = is_ptr
        return type

    @classmethod
    def new_function_type(cls, arg: Type, ret: Type, name: str=None) -> Type:
        type = Type(AbstractType.function_classification)
        type.arg = arg
        type.ret = ret
        type._name = name
        return type

    @classmethod
    def new_product_type(cls, components: list[Type]) -> Type:
        type = Type(AbstractType.tuple_classification)
        type.components = components
        return type

    @classmethod
    def new_named_product_type(cls, components: list[Type], component_names : list[str], name : str=None, mod: AbstractModule = None) -> Type:
        type = Type(AbstractType.struct_classification)
        type.components = components
        type.component_names = component_names
        type._name = name
        type.mod = mod
        return type

    @classmethod
    def _unpack_colon_operator(cls, config: Config, asl: CLRList, mod: AbstractModule) -> Type:
        type_asl = asl[1]
        if type_asl.type == "fn_type":
            return cls.get_type_of(config, type_asl, mod)
        
        type_str = type_asl[0].value
        if type_asl.type == "type*":
            type_str += "*"
        elif type_asl.type == "type?":
            type_str += "?"
        
        found_type = mod.resolve_type_by(type_str)

        if found_type is not None:
            return found_type

        # Raise Exception here
        Raise.error(f"Could not find type {type_str} _unpack_colon_operator")

    @classmethod
    def lookup_type_in_mod(cls, new_type: Type, mod: AbstractModule):
        found_type = mod.resolve_type_by(new_type.name())
        if found_type is None:
            mod.add_type(new_type)
            return new_type
        return found_type

    @classmethod
    def _unpack_types_tuple(cls, asl: CLRList, mod: AbstractModule) -> list[Type]:
        if asl.type != "types" and asl.type != "type":
            raise Exception(f"expected asl to be of type 'types' or 'type'; got '{asl.type}' instead")

        components: list[CLRList] = []
        if asl.head().type == "types":
            components = asl.head()[:]
        else:
            components = [asl]

        types = [mod.resolve_type_by(t.head_value()) for t in components]
        return Type.new_product_type(types)

    @classmethod
    def _unpack_args_and_rets_to_fn_type(cls, 
            config: Config,
            mod: AbstractModule,
            args: CLRList = [], 
            rets: CLRList = []):

        arg_type = None if len(args) == 0 else Type.get_type_of(config, args[0], mod)
        ret_type = None if len(rets) == 0 else Type.get_type_of(config, rets[0], mod)
        return Type.new_function_type(arg_type, ret_type) 


    @classmethod
    def get_type_of(cls, config: Config, asl: CLRList, mod: AbstractModule):
        if asl.type == "prod_type":
            components = [Type._unpack_colon_operator(config, child, mod) for child in asl]
            new_type = Type.new_product_type(components)

        elif asl.type == "fn_type":
            arg_type = Type.get_type_of(config, asl[0], mod)
            ret_type = Type.get_type_of(config, asl[1], mod)
            new_type = Type.new_function_type(arg_type, ret_type)
    
        elif asl.type == "fn_type_out": 
            if isinstance(asl[0], CLRList) and asl[0].head_value() == "void":
                return None
            new_type = Type._unpack_types_tuple(asl[0], mod)

        elif asl.type == "fn_type_in":
            if len(asl) == 0:
                return None
            new_type = Type._unpack_types_tuple(asl[0], mod)

        elif asl.type == ":":
            return Type._unpack_colon_operator(config, asl, mod)

        elif asl.type == "create" or asl.type == "def":
            args = ValidationTransformFunction._get_args_from_function_asl(asl)
            rets = ValidationTransformFunction._get_rets_from_function_asl(asl)
            new_type = cls._unpack_args_and_rets_to_fn_type(config, mod, args, rets)

        elif asl.type == "struct":
            components = asl[1:]

            # need to filter by ":" to avoid "create" and "destroy" children
            new_type = Type.new_named_product_type(
                components = [Type.get_type_of(config, comp, mod) for comp in components if comp.type == ":"],
                component_names = [comp.head_value() for comp in components if comp.type == ":"],
                name = asl.head_value(),
                mod = mod)

            found_type = mod.resolve_type_by(new_type.name(), local=True)
            if found_type is None:
                mod.add_type(new_type)
                return new_type

            # TODO: this should be a Seer exception 
            raise Exception(f"already defined a struct of name {found_type.name()}")

        else:
            Raise.error(f"unknown type to index {asl.type}")

        return Type.lookup_type_in_mod(new_type, mod)

class Flags(AbstractFlags):
    is_ret = "is_ret"
    is_arg = "is_arg"

class Params(Validator.Params):
    attrs = ["config", "asl", "validator", "exceptions", "mod", "context", "flags"]

    def __init__(self, 
            config: Config, 
            asl: CLRList, 
            txt: str,
            mod: AbstractModule,
            context: AbstractModule,
            flags: Flags,
            struct_name: str,
            exceptions: list[AbstractException]
            ):

        self.config = config
        self.asl = asl
        self.txt = txt
        self.mod = mod
        self.context = context
        self.flags = flags
        self.struct_name = struct_name
        self.exceptions = exceptions

    def but_with(self,
            config : Config = None,
            asl : CLRList = None,
            txt: str = None,
            mod : AbstractModule = None,
            context : AbstractModule = None,
            flags : Flags = None,
            struct_name: str = None,
            exceptions: list[AbstractException] = None
            ):

        params = Params(
            config = self.config if config is None else config,
            asl = self.asl if asl is None else asl,
            txt = self.txt if txt is None else txt,
            mod = self.mod if mod is None else mod,
            context = self.context if context is None else context,
            flags = self.flags if flags is None else flags,
            struct_name = self.struct_name if struct_name is None else struct_name,
            exceptions = self.exceptions if exceptions is None else exceptions,
            )

        return params

    def report_exception(self, e: AbstractException):
        self.exceptions.append(e)

class Abort():
    def __init__(self):
        return

    
class SeerEnsure():
    @classmethod
    def struct_has_unique_names(cls, params: Params):
        names = [member[0].value for member in params.asl[1:]]
        if len(names) != len(set(names)):
            params.report_exception(
                Exceptions.RedefinedIdentifier(
                "some identifier was defined multiple times",
                params.asl.line_number))
            return Abort()

class IndexerTransformFunction(Indexer):
    @Indexer.for_these_types("start")
    def start_i(fn, params: Indexer.Params):
        for child in params.asl:
            fn.apply(params.but_with(asl=child))

    @Indexer.for_these_types("struct")
    def struct_i(fn, params: Indexer.Params):
        Type.get_type_of(params.config, params.asl, params.mod)
        for child in params.asl:
            fn.apply(params.but_with(asl=child, struct_name=params.asl.head_value()))

    @Indexer.for_these_types("mod")
    def mod_i(fn, params: Indexer.Params):
        child_mod = AbstractModule(name=params.asl[0].value, parent=params.mod)
        for child in params.asl:
            fn.apply(params.but_with(
                asl = child, 
                mod = child_mod))

    @Indexer.for_these_types("def")
    def def_i(fn, params: Indexer.Params):
        new_obj = Object(
            name = params.asl.head_value(),
            type = Type.get_type_of(params.config, params.asl, params.mod),
            mod = params.mod)
        params.mod.add_object(new_obj)

    @Indexer.for_these_types("create")
    def create_i(fn, params: Indexer.Params):
        new_obj = Object(
            name = "create_" + params.struct_name, 
            type = Type.get_type_of(params.config, params.asl, params.mod),
            mod = params.mod)
        params.mod.add_object(new_obj)

class ValidationTransformFunction(Validator):
    class Flags:
        is_ret = "is_ret"
        is_arg = "is_arg"

    @classmethod
    def resolve_object_by(cls, name : str, params:  Params, local : bool=False):
        # lookup from local scope first
        obj = params.context.resolve_object_by(name, local=False)
        if obj:
            return obj

        # lookup from module structure
        obj = params.mod.resolve_object_by(name, local=local)
        return obj

    @classmethod
    def _resolve_object_in_module(cls, asl: CLRList, params:  Params) -> Object:
        # if the resolution chain is 1 deep (special case)
        if isinstance(asl[0], CLRToken):
            mod = params.mod.get_child_module(asl[0].value)
        else:
            mod = cls._decend_module_structure(asl[0], params.mod)

        found_obj = mod.resolve_object_by(asl[1].value)
        if not found_obj:
            # try looking up create
            found_obj = mod.resolve_object_by("create_" + asl[1].value)
        return found_obj

    @classmethod
    def _resolve_type_in_module(cls, asl: CLRList, params: Params) -> Type:
        # if the resolution chain is 1 deep (special case)
        if isinstance(asl[0], CLRToken):
            mod = params.mod.get_child_module(asl[0].value)
        else:
            mod = cls._decend_module_structure(asl[0], params.mod)

        return mod.resolve_type_by(asl[1].value)

    @classmethod
    def _decend_module_structure(cls, asl: CLRList, mod: AbstractModule) -> AbstractModule:
        if isinstance(asl[0], CLRList) and asl[0].type == "::":
            mod = cls._decend_module_structure(cls, asl[0], mod)
        elif isinstance(asl[0], CLRToken):
            return mod.get_child_module(asl[0].value).get_child_module(asl[1].value)

        return mod.get_child_module(asl[1].value)

    @classmethod
    def _any_exceptions(cls, *args) -> bool:
        for arg in args:
            if isinstance(arg, Abort):
                return True
        return False
        

    @classmethod
    def init_params(cls, config: Config, asl: CLRList, txt: str):
        global_mod = AbstractModule("global")
        global_mod.add_type(Type.new_base_type("int"))
        global_mod.add_type(Type.new_base_type("str"))
        global_mod.add_type(Type.new_base_type("flt"))
        global_mod.add_type(Type.new_base_type("bool"))
        global_mod.add_type(Type.new_base_type("int*", is_ptr=True))
        global_mod.add_type(Type.new_base_type("str*", is_ptr=True))
        global_mod.add_type(Type.new_base_type("flt*", is_ptr=True))
        global_mod.add_type(Type.new_base_type("bool*", is_ptr=True))
        global_mod.add_type(Type.new_base_type("int?", is_ptr=True, nullable=True))
        global_mod.add_type(Type.new_base_type("str?", is_ptr=True, nullable=True))
        global_mod.add_type(Type.new_base_type("flt?", is_ptr=True, nullable=True))
        global_mod.add_type(Type.new_base_type("bool?", is_ptr=True, nullable=True)) 

        return Params(
            config=config, 
            asl=asl,
            txt=txt,
            mod=global_mod,
            context=global_mod,
            flags=Flags(),
            struct_name=None,
            exceptions=[])

    # terminal types are . :: ref fn
    # handled in call are fn, args, rets
    no_need = ["fn", "args", "rets"]

    unimpl = ['arr_type']
    no_action = ["start", "prod_type", "return", "seq", "params"]
    @Validator.for_these_types(no_action + unimpl)
    def ignore(fn, params:  Params):
        for child in params.asl:
            fn.apply(params.but_with(asl=child)) 

    @Validator.for_these_types("fn_type")
    def fn_type_(fn, params: Params):
        return Type.get_type_of(params.config, params.asl, params.mod)

    @Validator.for_these_types(".")
    def dot_(fn, params: Params):
        type: Type = fn.apply(params.but_with(asl=params.asl.head()))
        attr_name = params.asl[1].value
        attr_type = type.get_member_attribute_named(attr_name)
        params.asl.data = Object(attr_name, type, params.mod)
        return attr_type

    # this handle the case for a::b but not for a::b() as that is a call and 
    # will be unwrapped in the "call" handler
    @Validator.for_these_types("::")
    def scope_(fn, params: Params):
        return ValidationTransformFunction._resolve_type_in_module(params.asl, params)

    @Validator.for_these_types("tuple")
    def tuple_(fn, params: Params):
        types = []
        for child in params.asl:
            types.append(fn.apply(params.but_with(asl=child)))
            
        if ValidationTransformFunction._any_exceptions(*types):
            return Abort()
        params.asl.data = types
        new_type = Type.new_product_type(types)
        found_type = params.mod.resolve_type_by(new_type.name())
        if found_type:
            return found_type
        return new_type

    @Validator.for_these_types("cond")
    def cond_(fn, params: Params):
        for child in params.asl:
            fn.apply(params.but_with(asl=child))

    @Validator.for_these_types("if")
    def if_(fn, params: Params):
        for child in params.asl:
            fn.apply(params.but_with(
                asl=child, 
                context=AbstractModule(parent=params.context)))

    @Validator.for_these_types("while")
    def while_(fn, params: Params):
        fn.apply(params.but_with(
            asl=params.asl.head(),
            context=AbstractModule(parent=params.context)))

    @Validator.for_these_types(":")
    def colon_(fn, params: Params):
        typ = fn.apply(params.but_with(asl=params.asl[1]))
        new_obj = Object(
            name=params.asl.head_value(), 
            type=typ, 
            mod=params.mod, 
            is_ret=(Flags.is_ret in params.flags),
            is_arg=(Flags.is_arg in params.flags),
            is_ptr=typ.is_ptr)

        params.asl.data = new_obj
        params.context.add_object(new_obj)
        
        return new_obj.type

    @Validator.for_these_types("call")
    def call(fn, params: Params):
        # always validate the function params
        fn.apply(params.but_with(asl=params.asl[1]))

        # unpack the (fn #value) member
        if params.asl.head().type == "fn":
            name= params.asl[0][0].value
            # TODO: formalize
            if name == "print":
                return Abort()
            found_obj = ValidationTransformFunction.resolve_object_by(name, params)
        elif params.asl.head().type == "::":
            found_obj = ValidationTransformFunction._resolve_object_in_module(params.asl[0], params)
            if found_obj is None:
                exit()

        if found_obj is None:
            params.report_exception(
                Exceptions.UndefinedVariable(
                f"'{name}' was never defined",
                params.asl.line_number))
            return Abort()

        params.asl.data = found_obj
        return found_obj.type.ret
         
    @Validator.for_these_types("struct")
    def struct(fn, params: Params):
        name = params.asl.head_value()
        params.asl.data = Object(
            name = name,
            type = params.mod.resolve_type_by(name),
            mod = params.mod)
        # SeerEnsure.struct_has_unique_names(params)
        # pass struct name into context so the create method knows where it is defined
        for child in params.asl[1:]:
            fn.apply(params.but_with(asl=child, context=AbstractModule(name=name)))

    @Validator.for_these_types("mod")
    def mod(fn, params: Params):
        name = params.asl[0].value
        child_mod = params.mod.get_child_module(name)
        for child in params.asl:
            fn.apply(params.but_with(asl=child, mod=child_mod))
 


    ################################################################################################
    # Functions and function likes
    @classmethod
    def _get_args_from_function_asl(cls, asl: CLRList):
        if asl.type == "def":
            return asl[1]
        elif asl.type == "create":
            return asl[0]
        else:
            raise Exception(f"provided type not a function type; got '{asl.type}'")

    @classmethod
    def _get_rets_from_function_asl(cls, asl: CLRList):
        if asl.type == "def":
            return [] if len(asl) == 3 else asl[2]
        elif asl.type == "create":
            return [] if len(asl) == 2 else asl[1]
        else:
            raise Exception(f"provided type not a function type; got '{asl.type}'")

    @classmethod
    def _validate_function_object(cls, 
            fn,
            name: str, 
            args: CLRList, 
            rets: CLRList, 
            seq: CLRList, 
            params: Params):

        # object exists due to indexing
        obj: Object = params.mod.resolve_object_by(name)
        params.asl.data = obj
        fn_context = AbstractModule()

        # validate args
        for child in args:
            fn.apply(params.but_with(
                asl=child, 
                context=fn_context,
                flags=params.flags.but_with(Flags.is_arg)))

        # validate rets
        for child in rets:
            fn.apply(params.but_with(
                asl=child, 
                context=fn_context, 
                flags=params.flags.but_with(Flags.is_ret)))

        # validate seq
        fn.apply(params.but_with(
            asl=seq,
            context=fn_context))

        return obj.type


    @Validator.for_these_types("create")
    def create_(fn, params:Params):
        # context name will be the name of the struct
        return ValidationTransformFunction._validate_function_object(
            fn=fn,
            name="create_" + params.context.name,
            args=ValidationTransformFunction._get_args_from_function_asl(params.asl),
            rets=ValidationTransformFunction._get_rets_from_function_asl(params.asl),
            seq=params.asl[-1], 
            params=params)
    
    @Validator.for_these_types("def")
    def fn(fn, params: Params):
        return ValidationTransformFunction._validate_function_object(
            fn=fn,
            name=params.asl.head_value(),
            args=ValidationTransformFunction._get_args_from_function_asl(params.asl),
            rets=ValidationTransformFunction._get_rets_from_function_asl(params.asl), 
            seq=params.asl[-1], 
            params=params)


    ################################################################################################
    
    binary_ops = ['+', '-', '/', '*', '&&', '||', '<', '>', '<=', '>=', '==', '!=', '+=', '-=', '*=', '/='] 
    @Validator.for_these_types(binary_ops)
    def binary_ops(fn, params: Params):
        left_type = fn.apply(params.but_with(asl=params.asl[0]))
        right_type = fn.apply(params.but_with(asl=params.asl[1]))

        if ValidationTransformFunction._any_exceptions(left_type, right_type):
            return Abort()

        if left_type != right_type:
            params.report_exception(
                Exceptions.TypeMismatch(
                f"operator '{params.asl.type}' used with '{left_type.name()}' and '{right_type.name()}'",
                params.asl.line_number))
            return Abort()
        
        return left_type

    # cases for let:
    # - standard
    #       let x: int
    #       (let (: x (type int)))
    # - interence
    #       let x = 4
    #       (let x 4)
    # - multiple standard
    #       let x, y: int
    #       (let (: (tags x y) (type int)))
    # - multiple inference
    #       let x, y = 4, 4
    #       (let (tags x y ) (tuple 4 4))
    @Validator.for_these_types(['val', 'var', 'mut_val', 'mut_var', 'let'])
    def decls(fn, params:Params):
        if isinstance(params.asl[0], CLRList):
            if params.asl[0].type == ":":
                asl_to_instr = params.asl[0]
                names = [params.asl[0][0].value]
                types: list[Type] = [fn.apply(params.but_with(asl=params.asl[0][1]))]
            elif params.asl[0].type == "tags":
                asl_to_instr = params.asl
                names = [t.value for t in params.asl[0]]
                types: list[Type] = fn.apply(params.but_with(asl=params.asl[1])).components
        else:
            asl_to_instr = params.asl
            names = [params.asl.head_value()]
            types: list[Type] = [fn.apply(params.but_with(asl=params.asl[1]))]
        
        objs = []
        for name, typ in zip(names, types):
            if ValidationTransformFunction.resolve_object_by(name, params) is not None:
                params.report_exception(
                    Exceptions.RedefinedIdentifier(
                    f"'{name}' is already in use",
                    params.asl.line_number))
                return Abort()

            new_obj = Object(
                name, typ, params.mod, 
                is_let = params.asl.type == "let",
                is_mut = "mut" in params.asl.type,
                is_const = "val" in params.asl.type,
                is_var = "var" in params.asl.type,
                is_ptr = "val" in params.asl.type or "var" in params.asl.type or typ.is_ptr)

            print(new_obj)
            objs.append(new_obj)
            params.context.add_object(new_obj)

        asl_to_instr.data = objs
        # needed for let c: int = 5
        params.asl.data = objs
        return new_obj.type

    @Validator.for_these_types("type") 
    def _type1(fn, params: Params):
        name = params.asl.head_value()
        return params.mod.resolve_type_by(name)

    @Validator.for_these_types("type?") 
    def _type2(fn, params: Params):
        name = params.asl.head_value() + "?"
        return params.mod.resolve_type_by(name)

    @Validator.for_these_types("type*") 
    def _type3(fn, params: Params):
        name = params.asl.head_value() + "*"
        return params.mod.resolve_type_by(name)

    @Validator.for_these_types("=")
    def assigns(fn, params: Params):
        left_type = fn.apply(params.but_with(asl=params.asl[0]))
        right_type = fn.apply(params.but_with(asl=params.asl[1]))
        
        if ValidationTransformFunction._any_exceptions(left_type, right_type):
            return Abort()

        # if left_type != right_type:
        #     params.report_exception(
        #         Exceptions.TypeMismatch(
        #             msg = f"expected {left_type} but got {right_type}",
        #             line_number=params.asl.line_number))


        return left_type 

    @Validator.for_these_types("<-")
    def larrow_(fn, params:Params):
        left_type = fn.apply(params.but_with(asl=params.asl[0]))
        right_type = fn.apply(params.but_with(asl=params.asl[1]))

        if ValidationTransformFunction._any_exceptions(left_type, right_type):
            return Abort()

        return left_type

    @Validator.for_these_types("ref")
    def ref(fn, params:Params):
        name = params.asl.head_value()
        found_obj = ValidationTransformFunction.resolve_object_by(name, params)
        if found_obj is None:
            params.report_exception(
                Exceptions.UndefinedVariable(
                    f"'{name}' was never defined",
                    params.asl.line_number))
            return Abort()

        params.asl.data = found_obj
        return found_obj.type
            