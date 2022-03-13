from __future__ import annotations
from typing import Generic, TypeVar

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

        tab = "  "
        indent = tab * level
        return "\n".join([indent + part for part in s.split("\n")])

    def __str__(self):
        header = f"mod {self.name}\n"
        child_mod_str = "".join([str(child) for child in self.child_modules])
        formatted_child_mod_str = self._add_indent(child_mod_str)
        components = ""
        for v in self.context.objs_in_scope._objs.values():
            components += f"{v}\n"
        for v in self.context.types_in_scope._objs.values():
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
            raise Exception(f"Attempting to add existing object name '{name}")

        self._objs[name] = obj

    def resolve(self, name : str, local: bool = False) -> T:
        current_scope = self
        while current_scope is not None:
            obj = current_scope._objs.get(name, None)
            if local or obj is not None:
                return obj

            current_scope = current_scope._parent_scope
        
        return None
