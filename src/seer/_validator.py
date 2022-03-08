from __future__ import annotations
from os import kill
from typing import TypeVar, Generic

import alpaca
from alpaca.asts import CLRList, CLRToken
from alpaca.config import Config

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

class Context:
    def __init__(self, parent: Context = None):
        self.parent_context = parent
        parent_types_scope = None if parent is None else parent.types_in_scope
        parent_objs_scope = None if parent is None else parent.objs_in_scope

        self.types_in_scope: AbstractScope[Typing.Type] = \
            AbstractScope(parent_scope=parent_types_scope)
        self.objs_in_scope: AbstractScope[AbstractObject] = \
            AbstractScope(parent_scope=parent_objs_scope)

    def add_object(self, name : str, obj : AbstractObject):
        self.objs_in_scope.add(name, obj)

    def add_type(self, name : str, type : AbstractType):
        self.types_in_scope.add(name, type)

    def resolve_object_name(self, name: str, local: bool = False) -> AbstractObject:
        return self.objs_in_scope.resolve(name, local=local)

    def resolve_type_name(self, name: str, local: bool = False) -> AbstractType:
        return self.types_in_scope.resolve(name, local=local)


class AbstractModule():
    def __init__(self, name : str, parent_module : AbstractModule=None):
        self.name = name
        self.parent_module = parent_module
        parent_context = None if parent_module is None else parent_module.context
        self.context: Context = Context(parent=parent_context)
        self.child_modules : list[AbstractModule] = []

    def resolve_object_name(self, name : str, local : bool=False) -> AbstractObject:
        return self.context.resolve_object_name(name, local=local)

    def resolve_type_name(self, name : str, local : bool=False) -> AbstractType:
        return self.context.resolve_type_name(name, local=local)

    def add_child_module(self, module : AbstractModule):
        self.child_modules.append(module)

    def get_child_module(self, name : str):
        found_mods = [m for m in self.child_modules if m.name == name]
        return found_mods[0]

    def _add_indent(self, s : str, level : int=1):
        if not s:
            return ""

        tab = " "
        indent = tab * level
        return "\n".join([indent + part for part in s.split("\n")])

    def __str__(self):
        header = f"mod {self.name}\n"
        child_mod_str = "".join([str(child) for child in self.child_modules])
        formatted_child_mod_str = self._add_indent(child_mod_str)
        components = ""
        for k, v in self.scope._defined_objects.items():
            components += f"{v}\n"

        formatted_components_str = self._add_indent(components)
        return header + formatted_components_str + formatted_child_mod_str

T = TypeVar("T")
class AbstractScope(Generic[T]):
    def __init__(self, parent_scope : AbstractScope[T] = None):
        self._parent_scope = parent_scope
        self._objs : dict[str, T] = {}

    def add(self, name : str, obj : T):
        if name in self._objs:
            Raise.error(f"Attempting to add existing object {name} {obj}")

        self._objs[name] = obj

    def resolve(self, name : str, local: bool = False) -> T:
        current_scope = self
        while current_scope is not None:
            obj = current_scope._objs.get(name, None)
            if local or obj is not None:
                return obj

            current_scope = current_scope._parent_scope
        
        return None

class ValidateFunctions():
    _indexed_function_prefix = "__alpaca_indexer_"
    class _ValidatorFunction():
        def __init__(self, f : Typing.Any, handles : list[str]):
            self.f = f
            self._handles = handles

        def handles(self, type : str):
            return type in self._handles
        
    def handle(self, node : str):
        attrs = dir(self)
        fns = [getattr(self, k) for k in attrs 
            if isinstance(getattr(self, k), ValidateFunctions._ValidatorFunction)]
        matching_fn = [f for f in fns if f.handles(node)]
        
        if not matching_fn:
            Raise.error(f"Could not match type given of {node}")
        if len(matching_fn) > 1:
            Raise.error(f"More than one match for {node}")

        return matching_fn[0].f

    @classmethod
    def indexes(cls, names : list[str] | str):
        if isinstance(names, str):
            names = [names]

        def decorator(f):
            return ValidateFunctions._ValidatorFunction(f, names)

        return decorator

    def _index(self, name : str, *args, **kwargs):
        f_name = f"indexer_{name}"
        if not hasattr(self, f_name):
            Raise.error(f"Validator has no @indexer decorated method {name}")

        f = getattr(self, f_name)
        f(*args, **kwargs) 

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




def _index(config : Config, asl : CLRList, mod : AbstractModule, validator : ValidateFunctions) -> None:
    for child in asl:
        if child.type == "struct":
            Typing.get_type_of(child, mod)

    for child in asl:
        if child.type == "mod":
            child_mod = AbstractModule(child[0].value, parent_module=mod)
            mod.add_child_module(child_mod)
            _index(config, child, child_mod, validator)
        if child.type == "def":
            name = child[0].value
            type = Typing.get_type_of(child, mod)
            new_obj = AbstractObject(name, type, mod)
            mod.context.add_object(name, new_obj)

def index(config : Config, asl : CLRList, validator : ValidateFunctions) -> AbstractModule:
    # TODO: make this a config option
    if asl.type != "start":
        Raise.error(f"unexpected asl starting token; expected start, got {asl.type}")

    global_mod = AbstractModule(name="global")
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

    _index(config, asl, global_mod, validator)
    return global_mod


def validate(config : Config, asl : CLRList, validator : ValidateFunctions, txt : str):
    return Validator.run(config, asl, SeerValidation(), txt)


binary_ops = ['+', '-', '/', '*', '&&', '||', '<', '>', '<=', '>=', '==', '!=', '+=', '-=', '*=', '/=']
decls = ['val', 'var', 'mut_val', 'mut_var', 'let']

def _any_exceptions(*args) -> bool:
    for arg in args:
        if isinstance(arg, Abort):
            return True

    return False

class Abort():
    def __init__(self):
        return

class ValidateParams:
    attrs = ["config", "asl", "validator", "exceptions", "mod", "context", "flags"]

    def __init__(self, 
            config : Config, 
            asl : CLRList, 
            validatefunctions : ValidateFunctions,
            exceptions : list[Exceptions.AbstractException],
            mod : AbstractModule,
            context : Context,
            flags : str,
            ):

        self.config = config
        self.asl = asl
        self.functions = validatefunctions
        self.exceptions = exceptions
        self.mod = mod
        self.context = context
        self.flags = flags

    def has_flag(self, flag : str) -> bool:
        if self.flags is None:
            return False
        return flag in self.flags

    def derive_flags_including(self, flags : str) -> str:
        return self.flags + ";" + flags

    def but_with(self,
            config : Config = None,
            asl : CLRList = None,
            validatefunctions : ValidateFunctions = None,
            exceptions : list[Exceptions.AbstractException] = None,
            mod : AbstractModule = None,
            context : Context = None,
            flags : str = None,
            ):

        new_params = ValidateParams.new_from(self)
        if config is not None:
            new_params.config = config
        if asl is not None:
            new_params.asl = asl
        if validatefunctions is not None:
            new_params.functions = validatefunctions
        if exceptions is not None:
            new_params.exceptions = exceptions
        if mod is not None:
            new_params.mod = mod
        if context is not None:
            new_params.context = context
        if flags is not None:
            new_params.flags = flags
        
        return new_params

    @classmethod
    def new_from(cls, params : ValidateParams, overrides : dict = {}) -> ValidateParams:
        new_params = ValidateParams(
            params.config,
            params.asl,
            params.functions,
            params.exceptions,
            params.mod,
            params.context,
            params.flags,
            )

        for k, v in overrides:
            if k in ValidateParams.attrs:
                setattr(new_params, k, v)
        
        return new_params


class Validator():
    @classmethod
    def run(cls, config : Config, asl : CLRList, validator : ValidateFunctions, txt : str):
        exceptions : list[Exceptions.AbstractException] = []
        global_mod = index(config, asl, validator)
        vparams = ValidateParams(
            config, 
            asl, 
            validator, 
            exceptions, 
            global_mod, 
            global_mod.context, 
            "")

        Validator.validate(vparams)

        for e in exceptions:
            print(e.to_str_with_context(txt))

        return global_mod

    def validate(params : ValidateParams):
        if isinstance(params.asl, CLRToken):
            return params.mod.resolve_type_name(params.asl.type)

        f = params.functions.handle(params.asl.type)
        return f(params)
        

class SeerEnsure():
    @classmethod
    def struct_has_unique_names(cls, params : ValidateParams):
        names = [member[0].value for member in params.asl[1:]]
        if len(names) != len(set(names)):
            e = Exceptions.RedefinedIdentifier(
                "some identifier was defined multiple times",
                params.asl.line_number)
            params.exceptions.append(e)


class SeerValidation(ValidateFunctions):
    class Flags:
        is_ret = "is_ret"


    @classmethod
    def resolve_object_name(cls, name : str, params : ValidateParams, local : bool=False):
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
    def _resolve_object_in_module(cls, asl : CLRList, params : ValidateParams) -> AbstractObject:
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

        




    unimpl = ['start', 'fn', 'args', 'arr_type', 'seq', 'rets', 'return', 'prod_type']

    @ValidateFunctions.indexes("while")
    def while_(params: ValidateParams):
        cond = params.asl[0]
        Validator.validate(params.but_with(asl=cond[0]))
        Validator.validate(params.but_with(asl=cond[1]))

    @ValidateFunctions.indexes(":")
    def colon_(params : ValidateParams):
        name_token = params.asl[0]
        name = name_token.value
        type = Validator.validate(params.but_with(asl=params.asl[1]))
        new_obj = AbstractObject(name, type, params.mod, is_ret=params.has_flag(SeerValidation.Flags.is_ret))
        params.asl.data = new_obj
        params.context.add_object(
            name, 
            new_obj)
        return type

    @ValidateFunctions.indexes("params")
    def params_(params : ValidateParams):
        for child in params.asl:
            Validator.validate(params.but_with(asl=child))

    @ValidateFunctions.indexes("call")
    def call(params : ValidateParams):
        # always validate the function params
        Validator.validate(params.but_with(asl=params.asl[1]))

        # unpack the (fn #value) member
        if params.asl[0].type == "fn":
            name= params.asl[0][0].value
            # TODO: formalize
            if name == "print":
                return Abort()
            found_obj = SeerValidation.resolve_object_name(name, params)
        else:
            found_obj = SeerValidation._resolve_object_in_module(params.asl[0], params)

        if found_obj is None:
            e = Exceptions.UndefinedVariable(
                f"'{name}' was never defined",
                params.asl.line_number)
            params.exceptions.append(e)
            return Abort()

        params.asl.data = found_obj
        return found_obj.type
         
    @ValidateFunctions.indexes('struct')
    def struct(params : ValidateParams):
        name_token = params.asl[0]
        name = name_token.value
        type = params.mod.resolve_type_name(name)
        params.asl.data = AbstractObject(name, type, params.mod)
        SeerEnsure.struct_has_unique_names(params)
        for child in params.asl[1:]:
            Validator.validate(params.but_with(asl=child, context=Context()))

    @ValidateFunctions.indexes('mod')
    def mod(params : ValidateParams):
        name = params.asl[0].value
        child_mod = params.mod.get_child_module(name)
        return [Validator.validate(params.but_with(asl=child, mod=child_mod)) for child in params.asl] 

    @ValidateFunctions.indexes("def")
    def fn(params : ValidateParams):
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
                    flags=params.derive_flags_including(SeerValidation.Flags.is_ret)))

        Validator.validate(params.but_with(asl=params.asl[-1], context=fn_context))
        return obj.type

    binary_ops = ['+', '-', '/', '*', '&&', '||', '<', '>', '<=', '>=', '==', '!=', '+=', '-=', '*=', '/='] 
    @ValidateFunctions.indexes(binary_ops)
    def binary_ops(params : ValidateParams):
        left_type = Validator.validate(params.but_with(asl=params.asl[0]))
        right_type = Validator.validate(params.but_with(asl=params.asl[1]))

        if _any_exceptions(left_type, right_type):
            return Abort()

        if left_type != right_type:
            e = Exceptions.TypeMismatch(
                f"operator '{params.asl.type}' used with '{left_type.name()}' and '{right_type.name()}'",
                params.asl.line_number)
            params.exceptions.append(e)
            return Abort()
        
        return left_type

    @ValidateFunctions.indexes(['val', 'var', 'mut_val', 'mut_var', 'let'])
    def decls(params : ValidateParams):
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
        
        if SeerValidation.resolve_object_name(name, params) is not None:
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

    @ValidateFunctions.indexes(unimpl)
    def ignore(params : ValidateParams):
        return [Validator.validate(params.but_with(asl=child)) for child in params.asl]

    @ValidateFunctions.indexes(['type']) 
    def _type1(params : ValidateParams):
        name = params.asl[0].value
        return params.mod.resolve_type_name(name)

    @ValidateFunctions.indexes(['type?']) 
    def _type2(params : ValidateParams):
        name = params.asl[0].value + "?"
        return params.mod.resolve_type_name(name)

    @ValidateFunctions.indexes(['type*']) 
    def _type3(params : ValidateParams):
        name = params.asl[0].value + "*"
        return params.mod.resolve_type_name(name)

    @ValidateFunctions.indexes(['='])
    def assigns(params : ValidateParams):
        left_obj = Validator.validate(params.but_with(asl=params.asl[0]))
        right_obj = Validator.validate(params.but_with(asl=params.asl[1]))

        if _any_exceptions(left_obj, right_obj):
            return Abort()

        return left_obj

    @ValidateFunctions.indexes("ref")
    def ref(params : ValidateParams):
        name = params.asl[0].value
        found_obj = SeerValidation.resolve_object_name(name, params)
        if found_obj is None:
            e = Exceptions.UndefinedVariable(
                f"'{name}' was never defined",
                params.asl.line_number)
            params.exceptions.append(e)
            return Abort()

        params.asl.data = found_obj
        return found_obj.type
            