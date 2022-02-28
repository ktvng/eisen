from __future__ import annotations
from gc import get_objects
from inspect import ismemberdescriptor
from re import A
from typing import NewType

import alpaca
from alpaca.asts import CLRList, CLRToken
from alpaca.config import Config

from error import Raise

class AbstractObject():
    def __init__(self, 
            name : str, 
            type : AbstractType, 
            is_let : bool = False, 
            is_mut : bool = False, 
            is_const : bool = False):

        self.name = name
        self.type = type
        self.is_let = is_let
        self.is_mut = is_mut
        self.is_const = is_const

    def __str__(self) -> str:
        return f"{self.name}<{self.type.name()}>"

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


class AbstractModule():
    def __init__(self, name : str, parent_module : AbstractModule=None):
        self.name = name
        self.parent_module = parent_module
        self.scope : AbstractScope = AbstractScope()
        self.child_modules : list[AbstractModule] = []

    def resolve_object_name(self, name : str, local : bool=False) -> AbstractObject:
        current_module = self
        while current_module is not None:
            obj = current_module.scope.get_object_by_name(name)
            if local or obj is not None:
                return obj
            
            current_module = current_module.parent_module
        
        return None

    def resolve_type_name(self, name : str, local : bool=False) -> AbstractType:
        current_module = self
        while current_module is not None:
            type = current_module.scope.get_type_by_name(name)
            if local or type is not None:
                return type

            current_module = current_module.parent_module
        
        return None

    def add_child_module(self, module : AbstractModule):
        self.child_modules.append(module)



class AbstractScope():
    def __init__(self):
        self._defined_types = {}
        self._defined_objects = {}

    def get_object_by_name(self, name : str) -> AbstractObject:
        return self._defined_objects.get(name, None)

    def get_type_by_name(self, name : str) -> AbstractType:
        return self._defined_types.get(name, None)

    def add_object(self, name : str, obj : AbstractObject):
        self._defined_objects[name] = obj

    def add_type(self, name : str, type : AbstractType):
        self._defined_types[name] = type

class AbstractValidator():
    @classmethod
    def indexes(cls, name : str):
        def decorator(f):
            f.__name__ = f"indexer_{name}"
            return f

        return decorator

    def _index(self, name : str, *args, **kwargs):
        f_name = f"indexer_{name}"
        if not hasattr(self, f_name):
            Raise.error(f"Validator has no @indexer decorated method {name}")

        f = getattr(self, f_name)
        f(*args, **kwargs)

class Validator(AbstractValidator):
    @AbstractValidator.indexes("mod")
    def mod_(config : Config, asl : CLRList, parent_module : AbstractModule, fn, **kwargs):
        child_mod = AbstractModule(asl[0].value, parent_module=parent_module)
        parent_module.add_child_module[child_mod]
        fn(config, asl, child_mod, Validator)


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
    class Type(AbstractType):
        def __init__(self, type=None):
            self._name = None
            self.type = type
            self.components : list[Typing.Type] = []
            self.names : list[str] = []
            self.args : list[Typing.Type] = []
            self.rets : list[Typing.Type] = []
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
                return (self._equiv(self.args, o.arg) 
                    and self._equiv(self.rets, o.rets))
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
                args_names = [x.cannonical_name() for x in self.args]
                rets_names = [x.cannonical_name() for x in self.rets]
                return f"({', '.join(args_names)}) -> ({', '.join(rets_names)})"
            else:
                Raise.error("cannoncial_name not implemented")
            
    @classmethod
    def base_type(cls, name : str, nullable=False) -> Typing.Type:
        type = Typing.Type("base")
        type._name = name
        type.nullable=nullable
        return type

    @classmethod
    def function_type(cls, args : list[Typing.Type], rets : list[Typing.Type]) -> Typing.Type:
        type = Typing.Type("function")
        type.args = args
        type.rets = rets
        return type

    @classmethod
    def product_type(cls, components : list[Typing.Type]) -> Typing.Type:
        type = Typing.Type("product")
        type.components = components
        return type

    @classmethod
    def named_product_type(cls, components : list[Typing.Type], names : list[str], name : str=None) -> Typing.Type:
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
            new_type = Typing.product_type(components)
            found_type = mod.resolve_type_name(new_type.name())
            if found_type is None:
                mod.scope.add_type(new_type.name(), new_type)
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
            
            args_types = [Typing.get_type_of(arg, mod) for arg in args]
            rets_types = [Typing.get_type_of(ret, mod) for ret in rets]

            new_type = Typing.function_type(args_types, rets_types)
            found_type = mod.resolve_type_name(new_type.name())
            if found_type is None:
                mod.scope.add_type(new_type.name(), new_type)
                return new_type
            return found_type

        elif asl.type == "struct":
            name = asl[0].value
            components = asl[1:]

            component_names = [comp[0].value for comp in components if comp.type == ":"]
            component_types = [Typing.get_type_of(comp, mod) for comp in components if comp.type == ":"]

            new_type = Typing.named_product_type(component_types, component_names, name=name)
            found_type = mod.resolve_type_name(new_type.name(), local=True)
            if found_type is None:
                mod.scope.add_type(new_type.name(), new_type)
                return new_type
            
            # TODO: throw exception
            Raise.code_error(f"already defined a struct of name {name}")




def _index(config : Config, asl : CLRList, mod : AbstractModule, validator : AbstractValidator) -> None:
    for child in asl:
        if child.type == "struct":
            name = child[0].value
            type = Typing.get_type_of(child, mod)
    for child in asl:
        if child.type == "mod":
            child_mod = AbstractModule(child[0].value, parent_module=mod)
            mod.add_child_module(child_mod)
            _index(config, child, child_mod, validator)
        if child.type == "def":
            name = child[0].value
            type = Typing.get_type_of(child, mod)

def index(config : Config, asl : CLRList, validator : AbstractValidator) -> AbstractModule:
    # TODO: make this a config option
    if asl.type != "start":
        Raise.error(f"unexpected asl starting token; expected start, got {asl.type}")

    global_mod = AbstractModule(name="global")
    global_mod.scope.add_type("int", Typing.base_type("int"))
    global_mod.scope.add_type("str", Typing.base_type("str"))
    global_mod.scope.add_type("flt", Typing.base_type("flt"))
    global_mod.scope.add_type("bool", Typing.base_type("bool"))
    global_mod.scope.add_type("int?", Typing.base_type("int?", nullable=True))
    global_mod.scope.add_type("str?", Typing.base_type("str?", nullable=True))
    global_mod.scope.add_type("flt?", Typing.base_type("flt?", nullable=True))
    global_mod.scope.add_type("bool?", Typing.base_type("bool?", nullable=True))

    _index(config, asl, global_mod, validator)
    return global_mod


def validate(config : Config, asl : CLRList, validator : AbstractValidator, txt : str):
    global_mod = index(config, asl, validator)

    exceptions : list[Exceptions.AbstractException] = []
    _validate(asl, global_mod, exceptions)

    for e in exceptions:
        print(e.to_str_with_context(txt))

    print(global_mod.resolve_object_name("x"))


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

def _validate(
        asl : CLRList, 
        mod : AbstractModule, 
        exceptions : list[Exceptions.AbstractException]) -> AbstractType | AbstractObject | Abort:

    if isinstance(asl, CLRToken):
        return mod.resolve_type_name(asl.type)

    if asl.type in binary_ops:
        left_type = _validate(asl[0], mod, exceptions)
        right_type = _validate(asl[1], mod, exceptions)

        if _any_exceptions(left_type, right_type):
            return Abort()

        if left_type != right_type:
            e = Exceptions.TypeMismatch(
                f"operator '{asl.type}' used with '{left_type.name()}' and '{right_type.name()}'",
                asl.line_number)
            exceptions.append(e)
            return Abort()
            
        return left_type

    elif asl.type == "type":
        name = asl[0].value
        return mod.resolve_type_name(name)
    
    elif asl.type == "type?":
        name = asl[0].value + "?"
        return mod.resolve_type_name(name)

    elif asl.type == "ref":
        return mod.resolve_object_name(asl[0].value)

    elif asl.type == "<-":
        left_obj = _validate(asl[0], mod, exceptions)
        right_obj = _validate(asl[1], mod, exceptions)

        if _any_exceptions(left_obj, right_obj):
            return Abort()

        if not AbstractObject.copyable(left_obj, right_obj):
            e = Exceptions.MemoryTypeMismatch(
                f"who knows?",
                asl.line_number)
            exceptions.append(e)
            return Abort()

        return left_obj
        

    elif asl.type == "=":
        left_obj = _validate(asl[0], mod, exceptions)
        right_obj = _validate(asl[1], mod, exceptions)

        if _any_exceptions(left_obj, right_obj):
            return Abort()

        if not AbstractObject.assignable(left_obj, right_obj):
            e = Exceptions.MemoryTypeMismatch(
                f"who knows?",
                asl.line_number)
            exceptions.append(e)
            return Abort()

        return left_obj

    elif asl.type in decls:
        if isinstance(asl[0], CLRList) and asl[0].type == ":":
            name = asl[0][0].value
            type = _validate(asl[0][1], mod, exceptions)
        else:
            name = asl[0].value
            type = _validate(asl[1], mod, exceptions)
        if mod.resolve_object_name(name) is not None:
            e = Exceptions.RedefinedIdentifier(
                f"'{name}' is already in use",
                asl.line_number)
            exceptions.append(e)
            return Abort()

        is_let = asl.type == "let"
        is_mut = "mut" in asl.type
        is_const = "val" in asl.type
        new_obj = AbstractObject(name, type, is_let=is_let, is_mut=is_mut, is_const=is_const)
        mod.scope.add_object(
            name, 
            new_obj)

        return new_obj


    else:
        return [_validate(child, mod, exceptions) for child in asl]
