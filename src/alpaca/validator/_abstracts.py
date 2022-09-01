from __future__ import annotations
from typing import Literal, Any
from functools import wraps

_novel = "novel"
_tuple = "tuple"
_struct = "struct"
_function = "function"
_maybe = "maybe"
TypeConstruction = Literal["novel", "tuple", "struct", "function", "maybe"]

# TODO: can we make this a decorator or something?
class RecursiveContainer():
    @classmethod
    def make_callable(cls, obj, fn):
        @wraps(fn)
        def new_fn(*args, **kwargs):
            return RecursiveContainer.call(obj, fn, *args, **kwargs)
        return new_fn

    def call(obj, fn, *args, **kwargs):
        kwargs_copy = dict(kwargs)
        if "local" in kwargs_copy:
            del kwargs_copy["local"]
        result = fn(*args, **kwargs_copy)
        if (result is not None
                or obj.parent is None
                or kwargs.get("local") == True):
            return result

        return RecursiveContainer.call(obj.parent, getattr(obj.parent, fn.__name__), *args, **kwargs)

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        setattr(obj, "parent", None)
        obj.__init__(*args, **kwargs)
        fns = [f for f in dir(obj) if f.startswith("resolve")]
        for fname in fns:
            new_f = RecursiveContainer.make_callable(obj, getattr(obj, fname))
            setattr(obj, fname, new_f)
        return obj

class Type():
    def __init__(self, 
            name: str, 
            construction: TypeConstruction,
            components: list[Type] = [],
            component_names: list[str] = []):

        self.name = name
        self.construction = construction
        self.components = components
        self.component_names = component_names

        if component_names and len(component_names) != len(components):
            raise Exception("Types must have the same number of components as component names.")

    def _equiv(self, u : list, v : list) -> bool:
        return (u is not None 
            and v is not None 
            and len(u) == len(v) 
            and all([x == y for x, y in zip(u, v)]))

    def __eq__(self, o: Any) -> bool:
        # TODO: can we return hash == hash here?
        if not isinstance(o, Type):
            return False
        if self.construction == _novel and o.construction == _novel:
            return self.name == o.name
        return (self._equiv(self.components, o.components)
            and self._equiv(self.component_names, o.component_names))

    def _get_unique_string_id(self) -> str:
        if self.construction == _novel:
            return self.name

        if self.component_names:
            member_strs = [f"{member_name}:{member._get_unique_string_id()}" 
                for member_name, member in zip(self.component_names, self.components)]
        else:
            member_strs = [member._get_unique_string_id() for member in self.components] 

        return f"{self}[{', '.join(member_strs)}]"

    def __hash__(self) -> int:
        return hash(self._get_unique_string_id())
        
    def __str__(self) -> str:
        return f"<{self.name}({self.construction})>"

    def get_member_attribute_by_name(self, name: str) -> Type:
        if self.construction != _struct:
            raise Exception(f"Can only get_member_attribute_by_name on struct types, got {self}")

        if name not in self.component_names:
            raise Exception(f"Type {self} does not have member attribute named '{name}'")

        pos = self.component_names.index(name)
        return self.components[pos]

class TypeFactory:
    @classmethod
    def produce_novel_type(cls, name: str) -> Type:
        return Type(name, _novel)

    @classmethod
    def produce_tuple_type(cls, components: list[Type], name: str = "") -> Type:
        return Type(name, _tuple, components)

    @classmethod
    def produce_struct_type(cls, name: str, components: list[Type], component_names: list[str]) -> Type:
        return Type(name, _struct, components, component_names)

    # a function is represented as a "function" classification with argument and return 
    # values being the two components, respectively
    @classmethod
    def produce_function_type(cls, arg: Type, ret: Type, name: str = ""):
        return Type(name, _function, [arg, ret])

    @classmethod
    def produce_maybe_type(cls, components: list[Type], name: str = ""):
        return Type(name, _maybe, components)

class TypeContainer:
    def __init__(self):
        self._types: list[Type] = []

    def obtain(self, type: Type):
        if type in self._types:
            pos = self._types.index(type)
            return self._types[pos]

        return None

    def add(self, type: Type):
        if type not in self._types:
            self._types.append(type)

    def copy(self) -> TypeContainer:
        new_container = TypeContainer()
        for type in self._types:
            new_container._types.append(type)
        return new_container

class Module(RecursiveContainer):
    def __init__(self, name: str, parent: Module = None, types: TypeContainer = None):
        self.name = name
        if types:
            self.types = types.copy()
        else:
            self.types = TypeContainer()

        self.children = []
        self.parent = parent
        if parent:
            parent._add_child(self)

    def _add_child(self, child: Module):
        self.children.append(child)

    def resolve_type(self, type: Type) -> Type:
        return self.types.obtain(type)

    def add_type(self, type: Type):
        self.types.add(type)

    def get_child_module_by_name(self, name: str) -> Module:
        child_module_names = [m.name for m in self.children]
        if name in child_module_names:
            pos = child_module_names.index(name)
            return self.children[pos]

        raise Exception(f"Wnable to resolve module named {name} inside module {self.name}")







########################## OLD
class AbstractType:
    classifications = ["base", "tuple", "struct", "function"]
    base_classification = "base"
    tuple_classification = "tuple"
    struct_classification = "struct"
    function_classification = "function"

    def __init__(self, classification: str):

        self._name = None
        self.classification = classification
        self.mod = None
        self.components: list[AbstractType] = []
        self.component_names : list[str] = []
        self.arg: AbstractType = None
        self.ret: AbstractType = None
        self.nullable = False
        self.is_ptr = False

    def _equiv(self, u : list, v : list) -> bool:
        return (u is not None 
            and v is not None 
            and len(u) == len(v) 
            and all([x == y for x, y in zip(u, v)]))

    def __eq__(self, o) -> bool:
        if not isinstance(o, AbstractType): return False
        if self.classification != o.classification: return False

        if self.classification == AbstractType.base_classification:
            return self._name == o._name
        elif self.classification == AbstractType.tuple_classification:
            return self._equiv(self.components, o.components)
        elif self.classification == AbstractType.struct_classification:
            return (self._equiv(self.components, o.components) 
                and self._equiv(self.component_names, o.component_names))
        elif self.classification == AbstractType.function_classification:
            return (self.arg == o.arg
                and self.ret == o.ret)
        else:
            raise Exception(f"AbstractType  __eq__ unimplemented for classification {self.classification}")

    def name() -> str:
        pass

class AbstractObject:
    def __init__(self, name):
        self.name = name
 
class AbstractModule(RecursiveContainer):
    def __init__(self, name: str = "", parent: AbstractModule = None):
        self.name = name
        self.parent = parent
        self.children = []
        self.objects: dict[AbstractObject] = {}
        self.types: dict[AbstractType] = {}

        if parent:
            parent._add_child(self)

    def add_object(self, obj: AbstractObject):
        if obj.name in self.objects:
            raise Exception(f"object name collision on {obj.name} in module {self.name}")
        self.objects[obj.name] = obj
    
    def add_type(self, typ: AbstractType):
        if typ.name() in self.types:
            raise Exception(f"type name collision on {typ.name()} in module {self.name}")
        self.types[typ.name()] = typ

    def resolve_object_by(self, name: str) -> AbstractObject:
        return self.objects.get(name, None)

    def resolve_type_by(self, name: str) -> AbstractType:
        return self.types.get(name, None)

    def get_child_module(self, name : str) -> AbstractModule:
        found_mods = [m for m in self.children if m.name == name]
        if not found_mods:
            raise Exception(f"unable to resolve module named {name} inside {self.name}")
        return found_mods[0]

    def _add_child(self, child: AbstractModule):
        self.children.append(child)

class AbstractException():
    delineator = "="*80+"\n"
    type = None
    description = None

    def __init__(self, msg : str, line_number : int):
        self.msg = msg
        self.line_number = line_number
        self._stub = None

    def __str__(self):
        padding = " "*len(str(self.line_number))
        return (AbstractException.delineator
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