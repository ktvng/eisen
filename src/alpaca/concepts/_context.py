from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from alpaca.concepts._instance import Instance
from alpaca.concepts._type import Type



class Context():
    def __init__(self, name: str, type: str, parent: Context = None):
        self.name = name
        self.type = type
        self.types: list[Type] = []

        self.children = []
        self.parent = parent
        self.instances: dict[str, Instance] = {}
        if parent:
            parent._add_child(self)

    def _add_child(self, child: Context):
        self.children.append(child)

    def _find_instance(self, name: str) -> Instance | None:
        if name in self.instances:
            return self.instances[name]
        if self.parent:
            return self.parent._find_instance(name)
        return None

    def resolve_instance(self, name: str, type: Type) -> Instance:
        found_instance = self._find_instance(name)
        if found_instance:
            return found_instance

        return self.add_instance(name, type)

    def get_instance_by_name(self, name: str) -> Instance | None:
        return self._find_instance(name)

    def add_instance(self, instance: Instance) -> Instance:
        self.instances[instance.name] = instance
        return instance

    def _find_type(self, type: Type) -> Type | None:
        if type in self.types:
            return type
        if self.parent:        
            return self.parent._find_type(type)
        return None

    def resolve_type(self, type: Type) -> Type:
        found_type = self._find_type(type)
        if found_type:
            return found_type

        self.add_type(type)
        return type

    def get_type_by_name(self, name: str) -> Type | None:
        type_names = [type.name for type in self.types]
        if name in type_names:
            pos = type_names.index(name)
            return self.types[pos]

        if self.parent:
            return self.parent.get_type_by_name(name)
        return None        

    def get_module_of_type(self, name: str) -> Context | None:
        type_names = [type.name for type in self.types]
        if name in type_names:
            return self

        if self.parent:
            return self.parent.get_module_of_type(name)
        return None        


    def add_type(self, type: Type):
        self.types.append(type)

    def get_child_module_by_name(self, name: str) -> Context:
        child_module_names = [m.name for m in self.children]
        if name in child_module_names:
            pos = child_module_names.index(name)
            return self.children[pos]

        raise Exception(f"Wnable to resolve module named {name} inside module {self.name}")

    def __str__(self) -> str:
        sub_module_lines = []
        for child in self.children:
            sub_module_lines.extend(str(child).split("\n"))
        object_lines = [str(instance) for instance in self.instances.values()]
        types_lines = [str(type) for type in self.types]
        sub_text_lines = types_lines + object_lines + sub_module_lines
        indented_subtext = "\n".join(["  | " + line for line in sub_text_lines if line])
        return f"{self.type} {self.name}\n{indented_subtext}"
        