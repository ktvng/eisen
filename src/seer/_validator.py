from __future__ import annotations

from alpaca.asts import CLRList, CLRToken
from alpaca.config import Config
from alpaca.validator import Indexer, Validator, AbstractModule, Context

from error import Raise

class AbstractObject():
    def __init__(self, 
            name : str, 
            type : AbstractType, 
            mod : AbstractModule,
            is_let : bool = False, 
            is_mut : bool = False, 
            is_const : bool = False,
            is_ret : bool = False):

        self.name = name
        self.type = type
        self.mod = mod
        self.is_let = is_let
        self.is_mut = is_mut
        self.is_const = is_const
        self.is_ret = is_ret

    def __str__(self) -> str:
        return f"{self.name}<{self.type.cannonical_name()}>"

    @classmethod
    def assignable(cls, left_obj : AbstractObject, right_obj : AbstractObject):
        if left_obj.is_let or left_obj.is_const:
            return False
        
        if left_obj.is_mut:
            return right_obj.is_mut
        
        return True

    @classmethod
    def copyable(cls, left_obj : AbstractObject, right_obj : AbstractObject):
        if left_obj.is_let:
            return True

        return False

class AbstractType():
    pass

class Exceptions():
    delineator = "="*80+"\n"

    class AbstractException():
        type = None
        description = None

        def __init__(self, msg : str, line_number : int):
            self.msg = msg
            self.line_number = line_number
            self._stub = None

        def __str__(self):
            padding = " "*len(str(self.line_number))
            return (Exceptions.delineator
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
                line = f"       {c} {i+1} \t| {lines[i]}\n" 
                str_rep += line
                
            return str_rep

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

class Typing:
    types = ["function", "product", "named_product", "or", "base", "struct"]
    base_type_name = "base"
    function_type_name = "function"
    product_type_name = "product"
    or_type_name = "or"
    struct_type_name = "struct"

    class Type(AbstractType):
        def __init__(self, type=None):
            self._name = None
            self.type = type
            self.components : list[Typing.Type] = []
            self.names : list[str] = []
            self.arg: Typing.Type = None
            self.ret: Typing.Type = None
            self.nullable = False
        
        def _equiv(self, u : list, v : list) -> bool:
            return (u is not None and v is not None 
                and len(u) == len(v) and all([x == y for x, y in zip(u, v)]))

        def name(self):
            if self._name is not None:
                return self._name
            
            return self.cannonical_name()

        def __eq__(self, o: object) -> bool:
            if not isinstance(o, Typing.Type):
                return False

            if self.type != o.type:
                return False

            if self.type == "base":
                return self._name == o._name
            elif self.type == "product":
                return self._equiv(self.components, o.components)
            elif self.type == "named_product":
                return (self._equiv(self.components, o.components) 
                    and self._equiv(self.names, o.names))
            elif self.type == "function":
                return (self.arg == o.arg
                    and self.ret == o.ret)
            else:
                Raise.error("Unimplemented __eq__ for Typing.Type")

        def cannonical_name(self) -> str:
            if self.type == "base":
                return self._name
            elif self.type == "product":
                component_type_strs = [x.cannonical_name() for x in self.components]
                return f"({', '.join(component_type_strs)})"
            elif self.type == "named_product":
                component_type_strs = [x.cannonical_name() for x in self.components]
                component_key_value_strs = [f"{name}:{type}" 
                    for name, type in zip(self.names, component_type_strs)]
                return f"({', '.join(component_key_value_strs)})"
            elif self.type == "function":
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
    def new_base_type(cls, name : str, nullable=False) -> Typing.Type:
        type = Typing.Type("base")
        type._name = name
        type.nullable=nullable
        return type

    @classmethod
    def new_function_type(cls, arg: Typing.Type, ret: Typing.Type, name : str=None) -> Typing.Type:
        type = Typing.Type("function")
        type.arg = arg
        type.ret = ret
        type._name = name
        return type

    @classmethod
    def new_product_type(cls, components : list[Typing.Type]) -> Typing.Type:
        type = Typing.Type("product")
        type.components = components
        return type

    @classmethod
    def new_named_product_type(cls, components : list[Typing.Type], names : list[str], name : str=None) -> Typing.Type:
        type = Typing.Type("named_product")
        type.components = components
        type.names = names
        type._name = name
        return type

    @classmethod
    def _unpack_colon_operator(cls, asl : CLRList, mod : AbstractModule) -> Typing.Type:
        type_asl = asl[1]
        type_str = type_asl[0].value

        found_type = mod.resolve_type_name(type_str)
        if found_type is not None:
            return found_type

        # Raise Exception here
        Raise.error(f"Could not find type {type_str} _unpack_colon_operator")

    @classmethod
    def get_type_of(cls, asl : CLRList, mod : AbstractModule):
        if asl.type == "prod_type":
            components = [Typing._unpack_colon_operator(child, mod) for child in asl]
            new_type = Typing.new_product_type(components)
            found_type = mod.resolve_type_name(new_type.name())
            if found_type is None:
                mod.context.add_type(new_type.name(), new_type)
                return new_type
            return found_type

        elif asl.type == ":":
            return Typing._unpack_colon_operator(asl, mod)
        
        elif asl.type == "def":
            name = asl[0].value
            args = asl[1]
            rets = []
            if len(asl) == 4:
                rets = asl[2]

            if len(args) == 0:
                arg_type = None
            else:
                arg_type = Typing.get_type_of(args[0], mod)

            if len(rets) == 0:
                ret_type = None 
            else:
                ret_type = Typing.get_type_of(rets[0], mod)

            # don't use name because functions are not named types
            new_type = Typing.new_function_type(arg_type, ret_type)
            found_type = mod.resolve_type_name(new_type.name())
            if found_type is None:
                mod.context.add_type(new_type.name(), new_type)
                return new_type
            return found_type

        elif asl.type == "struct":
            name = asl[0].value
            components = asl[1:]

            component_names = [comp[0].value for comp in components if comp.type == ":"]
            component_types = [Typing.get_type_of(comp, mod) for comp in components if comp.type == ":"]

            new_type = Typing.new_named_product_type(component_types, component_names, name=name)
            found_type = mod.resolve_type_name(new_type.name(), local=True)
            if found_type is None:
                mod.context.add_type(new_type.name(), new_type)
                return new_type
            
            # TODO: throw exception
            Raise.code_error(f"already defined a struct of name {name}")

        else:
            Raise.error(f"unknown type to index {asl.type}")

class Abort():
    def __init__(self):
        return

    
class SeerEnsure():
    @classmethod
    def struct_has_unique_names(cls, params : Validator.Params):
        names = [member[0].value for member in params.asl[1:]]
        if len(names) != len(set(names)):
            e = Exceptions.RedefinedIdentifier(
                "some identifier was defined multiple times",
                params.asl.line_number)
            params.exceptions.append(e)


class Seer():
    class Flags:
        is_ret = "is_ret"

    @Indexer.for_these_types("start")
    def start_i(params: Indexer.Params):
        for child in params.asl:
            Indexer.index(params.but_with(asl=child))

    @Indexer.for_these_types("struct")
    def struct_i(params: Indexer.Params):
        Typing.get_type_of(params.asl, params.mod)

    @Indexer.for_these_types("mod")
    def mod_i(params: Indexer.Params):
        child_mod = AbstractModule(params.asl[0].value, parent_module=params.mod)
        params.mod.add_child_module(child_mod)
        for child in params.asl:
            Indexer.index(params.but_with(asl=child, mod=child_mod))

    @Indexer.for_these_types("def")
    def def_i(params: Indexer.Params):
        name = params.asl.head_value()
        type = Typing.get_type_of(params.asl, params.mod)
        new_obj = AbstractObject(name, type, params.mod)
        params.mod.context.add_object(name, new_obj)

    @Indexer.initialize_by
    def initialize_i(config: Config, asl: CLRList, global_mod: AbstractModule) -> Indexer.Params: 
        global_mod.context.add_type("int", Typing.new_base_type("int"))
        global_mod.context.add_type("str", Typing.new_base_type("str"))
        global_mod.context.add_type("flt", Typing.new_base_type("flt"))
        global_mod.context.add_type("bool", Typing.new_base_type("bool"))
        global_mod.context.add_type("int*", Typing.new_base_type("int*"))
        global_mod.context.add_type("str*", Typing.new_base_type("str*"))
        global_mod.context.add_type("flt*", Typing.new_base_type("flt*"))
        global_mod.context.add_type("bool*", Typing.new_base_type("bool*"))
        global_mod.context.add_type("int?", Typing.new_base_type("int?", nullable=True))
        global_mod.context.add_type("str?", Typing.new_base_type("str?", nullable=True))
        global_mod.context.add_type("flt?", Typing.new_base_type("flt?", nullable=True))
        global_mod.context.add_type("bool?", Typing.new_base_type("bool?", nullable=True)) 

        return Indexer.Params(config, asl, global_mod, Seer)




    @classmethod
    def resolve_object_name(cls, name : str, params : Validator.Params, local : bool=False):
        # lookup from local scope first
        obj = params.context.resolve_object_name(name, local=False)
        if obj:
            return obj

        # lookup from module structure
        obj = params.mod.resolve_object_name(name, local=local)
        return obj

    @classmethod
    def _struct_has_unique_names(cls, asl : CLRList):
        names = [member[0].value for member in asl[1:]]
        return len(names) == len(set(names))

    @classmethod
    def _get_global_module(cls, mod : AbstractModule) -> AbstractModule:
        next_mod = mod.parent_module
        while next_mod is not None:
            mod = next_mod
            next_mod = mod.parent_module

        return mod

    @classmethod
    def _resolve_object_in_module(cls, asl : CLRList, params : Validator.Params) -> AbstractObject:
        global_mod = cls._get_global_module(params.mod)
        # if the resolution chain is 1 deep (special case)
        if isinstance(asl[0], CLRToken):
            mod = global_mod.get_child_module(asl[0].value)
        else:
            mod = cls._decend_module_structure(asl[0], global_mod)
            

        return mod.context.resolve_object_name(asl[1].value)

    @classmethod
    def _decend_module_structure(cls, asl : CLRList, mod : AbstractModule) -> AbstractModule:
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
        




    unimpl = ['start', 'fn', 'args', 'arr_type', 'seq', 'rets', 'return', 'prod_type']

    @Validator.for_these_types(".")
    def dot_(params: Validator.Params):
        # TODO: this needs to be fixed now
        for child in params.asl:
            Validator.validate(params.but_with(asl=child))
        

    @Validator.for_these_types("tuple")
    def tuple_(params: Validator.Params):
        objs = []
        for child in params.asl:
            objs.append(Validator.validate(params.but_with(asl=child)))

        params.asl.data = objs


    @Validator.for_these_types("while")
    def while_(params: Validator.Params):
        cond = params.asl[0]
        Validator.validate(params.but_with(asl=cond[0]))
        Validator.validate(params.but_with(asl=cond[1]))

    @Validator.for_these_types(":")
    def colon_(params : Validator.Params):
        name_token = params.asl[0]
        name = name_token.value
        type = Validator.validate(params.but_with(asl=params.asl[1]))
        new_obj = AbstractObject(name, type, params.mod, is_ret=params.has_flag(Seer.Flags.is_ret))
        params.asl.data = new_obj
        params.context.add_object(
            name, 
            new_obj)
        return type

    @Validator.for_these_types("params")
    def params_(params : Validator.Params):
        for child in params.asl:
            Validator.validate(params.but_with(asl=child))

    @Validator.for_these_types("call")
    def call(params : Validator.Params):
        # always validate the function params
        Validator.validate(params.but_with(asl=params.asl[1]))

        # unpack the (fn #value) member
        if params.asl[0].type == "fn":
            name= params.asl[0][0].value
            # TODO: formalize
            if name == "print":
                return Abort()
            found_obj = Seer.resolve_object_name(name, params)
        else:
            found_obj = Seer._resolve_object_in_module(params.asl[0], params)

        if found_obj is None:
            e = Exceptions.UndefinedVariable(
                f"'{name}' was never defined",
                params.asl.line_number)
            params.exceptions.append(e)
            return Abort()

        params.asl.data = found_obj
        return found_obj.type
         
    @Validator.for_these_types('struct')
    def struct(params : Validator.Params):
        name_token = params.asl[0]
        name = name_token.value
        type = params.mod.resolve_type_name(name)
        params.asl.data = AbstractObject(name, type, params.mod)
        SeerEnsure.struct_has_unique_names(params)
        for child in params.asl[1:]:
            Validator.validate(params.but_with(asl=child, context=Context()))

    @Validator.for_these_types('mod')
    def mod(params : Validator.Params):
        name = params.asl[0].value
        child_mod = params.mod.get_child_module(name)
        return [Validator.validate(params.but_with(asl=child, mod=child_mod)) for child in params.asl] 

    @Validator.for_these_types("def")
    def fn(params : Validator.Params):
        name_token = params.asl[0]
        name = name_token.value

        # object exists due to indexing
        obj = params.mod.context.resolve_object_name(name)
        params.asl.data = obj
        fn_context = Context()

        # validate args
        args = params.asl[1]
        for child in args:
            Validator.validate(params.but_with(asl=child, context=fn_context))

        # validate rets
        if len(params.asl) == 4:
            rets = params.asl[2]
            for child in rets:
                Validator.validate(params.but_with(
                    asl=child, 
                    context=fn_context, 
                    flags=params.derive_flags_including(Seer.Flags.is_ret)))

        Validator.validate(params.but_with(asl=params.asl[-1], context=fn_context))
        return obj.type

    binary_ops = ['+', '-', '/', '*', '&&', '||', '<', '>', '<=', '>=', '==', '!=', '+=', '-=', '*=', '/='] 
    @Validator.for_these_types(binary_ops)
    def binary_ops(params : Validator.Params):
        left_type = Validator.validate(params.but_with(asl=params.asl[0]))
        right_type = Validator.validate(params.but_with(asl=params.asl[1]))

        if Seer._any_exceptions(left_type, right_type):
            return Abort()

        if left_type != right_type:
            e = Exceptions.TypeMismatch(
                f"operator '{params.asl.type}' used with '{left_type.name()}' and '{right_type.name()}'",
                params.asl.line_number)
            params.exceptions.append(e)
            return Abort()
        
        return left_type

    @Validator.for_these_types(['val', 'var', 'mut_val', 'mut_var', 'let'])
    def decls(params : Validator.Params):
        if isinstance(params.asl[0], CLRList) and params.asl[0].type == ":":
            asl_to_instr = params.asl[0]
            name = params.asl[0][0].value
            type = Validator.validate(params.but_with(asl=params.asl[0][1]))
        else:
            asl_to_instr = params.asl
            if isinstance(params.asl[1], CLRList):
                Raise.code_error("unimplemented for decls = expr") 

            name = params.asl[0].value
            type = Validator.validate(params.but_with(asl=params.asl[1]))
        
        if Seer.resolve_object_name(name, params) is not None:
            e = Exceptions.RedefinedIdentifier(
                f"'{name}' is already in use",
                params.asl.line_number)
            params.exceptions.append(e)
            return Abort()

        is_let = params.asl.type == "let"
        is_mut = "mut" in params.asl.type
        is_const = "val" in params.asl.type
        new_obj = AbstractObject(name, type, params.mod, is_let=is_let, is_mut=is_mut, is_const=is_const)
        params.context.add_object(
            name, 
            new_obj)

        asl_to_instr.data = new_obj
        return new_obj.type

    @Validator.for_these_types(unimpl)
    def ignore(params : Validator.Params):
        return [Validator.validate(params.but_with(asl=child)) for child in params.asl]

    @Validator.for_these_types(['type']) 
    def _type1(params : Validator.Params):
        name = params.asl[0].value
        return params.mod.resolve_type_name(name)

    @Validator.for_these_types(['type?']) 
    def _type2(params : Validator.Params):
        name = params.asl[0].value + "?"
        return params.mod.resolve_type_name(name)

    @Validator.for_these_types(['type*']) 
    def _type3(params : Validator.Params):
        name = params.asl[0].value + "*"
        return params.mod.resolve_type_name(name)

    @Validator.for_these_types(['='])
    def assigns(params : Validator.Params):
        left_obj = Validator.validate(params.but_with(asl=params.asl[0]))
        right_obj = Validator.validate(params.but_with(asl=params.asl[1]))

        if Seer._any_exceptions(left_obj, right_obj):
            return Abort()

        return left_obj

    @Validator.for_these_types("ref")
    def ref(params : Validator.Params):
        name = params.asl[0].value
        found_obj = Seer.resolve_object_name(name, params)
        if found_obj is None:
            e = Exceptions.UndefinedVariable(
                f"'{name}' was never defined",
                params.asl.line_number)
            params.exceptions.append(e)
            return Abort()

        params.asl.data = found_obj
        return found_obj.type
            