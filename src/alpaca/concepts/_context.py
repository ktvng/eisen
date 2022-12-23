from __future__ import annotations
from typing import TYPE_CHECKING, Any

import uuid

if TYPE_CHECKING:
    from alpaca.concepts._instance import Instance
    from alpaca.concepts._typeclass import TypeClass

class Context():
    def __init__(self, name: str, type: str, parent: Context = None):
        self.name = name
        self.type = type
        self.containers = {
            "typeclass": {},
            "instance": {},
            "restriction": {},
        }
        self.typeclasses: list[TypeClass] = []
        self.objs: dict[str, Any] = {}

        self.children = []
        self.parent = parent
        self.instances: dict[str, Instance] = {}
        self.guid = uuid.uuid4()
        if parent and type == "module":
            parent._add_child(self)

    def _add_child(self, child: Context):
        self.children.append(child)

    # TODO: refactor to use add_obj instead of specialized for typeclass and stuff
    def add_obj(self, container_name: str, name: str, obj: Any):
        container = self.containers[container_name]
        container[name] = obj

    def get_obj(self, container_name: str, name: str) -> Any:
        local_result = self.get_local_obj(container_name, name)
        if local_result is not None:
            return local_result
        elif self.parent:
            return self.parent.get_obj(container_name, name)
        return None

    def get_local_obj(self, container_name: str, name: str) -> Any:
        container = self.containers[container_name]
        if name in container:
            return container[name]   
        return None


    def add_instance(self, instance: Instance) -> Instance:
        self.instances[instance.name] = instance
        return instance

    def find_instance(self, name: str) -> Instance | None:
        if name in self.instances:
            return self.instances[name]
        if self.parent:
            return self.parent.find_instance(name)
        return None

    def get_instance_by_name(self, name: str) -> Instance | None:
        return self.find_instance(name)



    def add_typeclass(self, typeclass: TypeClass):
        if typeclass not in self.typeclasses:
            self.typeclasses.append(typeclass)

    def get_typeclass_by_name(self, name: str) -> TypeClass:
        found_typeclass = [tc for tc in self.typeclasses if tc.name == name]
        if len(found_typeclass) == 1:
            return found_typeclass[0]
        if len(found_typeclass) > 1:
            raise Exception(f"expected exactly one typeclass, got {len(found_typeclass)}")

        if self.parent:
            return self.parent.get_typeclass_by_name(name)
        raise Exception(f"could not find typeclass {name}")

    def get_child_by_name(self, name: str) -> Context:
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
        types_lines = [("::" + str(type)).split("::")[-1] for type in self.typeclasses]
        sub_text_lines = types_lines + object_lines + [" "] + sub_module_lines
        indented_subtext = "\n".join(["  | " + line for line in sub_text_lines if line])
        return f"{self.type} {self.name}\n{indented_subtext}"
        
    def get_full_name(self) -> str:
        # case for the global module
        if self.parent is None:
            return ""

        name = self.name
        mod = self.parent
        while mod is not None and mod.parent is not None:
            name += mod.name + "::"
        return name