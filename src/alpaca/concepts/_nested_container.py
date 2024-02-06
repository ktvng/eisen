from __future__ import annotations
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from alpaca.concepts._type import Type

class NestedContainer():
    container_names = ["type", "instance", "instance_state", "function_instance"]

    def __init__(self, name: str, parent: NestedContainer = None):
        self.name = name
        self.containers = {}
        self._initialize_containers()

        self.children = []
        self.parent = parent
        if parent is not None:
            parent._add_child(self)

    def fork(self) -> Self:
        klass = type(self)
        new_container = klass(self.name, self.parent)
        for key in new_container.containers:
            new_container.containers[key] = self.containers[key].copy()
        new_container.children = self.children.copy()
        return new_container

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

    def get_all_local_objs(self, container_name: str) -> list[Any]:
        return self.containers[container_name].values()

    def get_local_obj(self, container_name: str, name: str) -> Any:
        container = self.containers[container_name]
        if name in container:
            return container[name]
        return None

    def _get_function_instance_key(self, name: str, type: Type) -> str:
        return name + "." + type.get_uuid_str()

    def add_function_instance(self, instance: Any) -> None:
        self.add_obj("function_instance",
            self._get_function_instance_key(
                instance.name, instance.type.get_argument_type()),
            instance)

    def get_function_instance(self, name: str, type: Type) -> Any | None:
        return self.get_obj("function_instance", self._get_function_instance_key(name, type))

    def get_all_function_instances_with_name(self, name: str) -> list[Any]:
        container = self.containers["function_instance"]
        function_instances = container.values()
        local_matching_instances = [fi for fi in function_instances if fi.name == name]
        if self.parent is None:
            return local_matching_instances
        return local_matching_instances + self.parent.get_all_function_instances_with_name(name)

    def __str__(self) -> str:
        sub_module_lines = []
        for child in self.children:
            sub_module_lines.extend(str(child).split("\n"))
        lines = ["== Functions ==\n"] + [str(instance) for instance in self.containers["function_instance"].values()]
        lines += ["== Instances ==\n"] + [str(instance) for instance in self.containers["instance"].values()]
        indented_subtext = "\n".join(["  | " + line for line in lines if line])
        return f"{self.name}\n{indented_subtext}"

    def get_full_name(self) -> str:
        name = ""
        mod = self
        while mod is not None:
            name = mod.name + "_" + name
            mod = mod.parent
        return name[:-1]
