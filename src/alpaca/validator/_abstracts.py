from __future__ import annotations
from typing import Generic, TypeVar
from functools import wraps

class AbstractType:
    def name() -> str:
        pass

class AbstractObject:
    def __init__(self, name):
        self.name = name

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
        