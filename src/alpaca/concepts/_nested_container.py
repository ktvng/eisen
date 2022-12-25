from __future__ import annotations
from typing import TYPE_CHECKING, Any

import uuid

if TYPE_CHECKING:
    from alpaca.concepts._instance import Instance
    from alpaca.concepts._typeclass import TypeClass
    from alpaca.concepts._instancestate import InstanceState

class NestedContainer():
    container_names = ["typeclass", "instance", "instance_state"]

    def __init__(self, name: str, type: str, parent: NestedContainer = None):
        self.name = name
        self.type = type
        self.containers = {}
        self._initialize_containers()

        self.children = []
        self.parent = parent
        self.guid = uuid.uuid4()
        if parent is not None:
            parent._add_child(self)

    def _initialize_containers(self) -> None:
        for name in self.container_names:
            self.containers[name] = {}

    def _add_child(self, child: NestedContainer):
        self.children.append(child)

    def get_child_by_name(self, name: str) -> NestedContainer:
        child_container_names = [m.name for m in self.children]
        if name in child_container_names:
            pos = child_container_names.index(name)
            return self.children[pos]

        raise Exception(f"Unable to resolve module named {name} inside module {self.name}")

    def add_obj(self, container_name: str, name: str, obj: Any):
        container = self.containers[container_name]
        container[name] = obj

    def get_obj(self, container_name: str, name: str) -> Any:
        local_result = self.get_local_obj(container_name, name)
        if local_result is not None:
            return local_result
        if self.parent:
            return self.parent.get_obj(container_name, name)
        return None

    def get_local_obj(self, container_name: str, name: str) -> Any:
        container = self.containers[container_name]
        if name in container:
            return container[name]   
        return None

    def add_instance(self, instance: Instance) -> None:
        self.add_obj("instance", instance.name, instance)

    def get_instance(self, name: str) -> Instance | None:
        return self.get_obj("instance", name)

    def add_typeclass(self, typeclass: TypeClass):
        if typeclass.name:
            self.add_obj("typeclass", typeclass.get_uuid_str(), typeclass)

    def get_typeclass(self, name: str) -> TypeClass:
        return self.get_obj("typeclass", name)

    def add_instancestate(self, instance_state: InstanceState) -> None:
        self.add_obj("instance_state", instance_state.name, instance_state)

    def get_instancestate(self, name: str) -> InstanceState:
        return self.get_obj("instance_state", name)


    def __str__(self) -> str:
        sub_module_lines = []
        for child in self.children:
            sub_module_lines.extend(str(child).split("\n"))
        object_lines = [str(instance) for instance in self.containers["instance"].values()]
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
