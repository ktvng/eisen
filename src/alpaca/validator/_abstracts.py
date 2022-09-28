from __future__ import annotations
from functools import wraps


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

class AbstractParams:
    def __init__(self, **kwargs):
        for key, val in kwargs.items():
            self.__setattr__(key, val)

    def _but_with(self, **kwargs) -> AbstractParams:
        filtered_kwargs = {}
        for k, v in kwargs.items():
            if v is not None:
                filtered_kwargs[k] = v
        # filtered_kwargs = dict({(k, v) for k, v in kwargs.items() if v is not None})
        updated_attrs = { **self.__dict__, **filtered_kwargs}
        return type(self)(**updated_attrs)


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