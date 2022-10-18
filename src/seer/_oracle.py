from __future__ import annotations
from typing import Any

from alpaca.concepts import Type, Context, Instance, TypeClass2
from alpaca.clr import CLRToken, CLRList

class Oracle:
    def __init__(self):
        self.nodes: dict[Any, dict[str, Any]] = {}

    def _get_node_property(self, node: Any, property_name: str) -> Any:
        key = node
        if isinstance(node, CLRList):
            key = node.guid

        node_data = self.nodes.get(key, None)
        if node_data is None:
            raise Exception(f"{node} has no associated data.")
        
        property = node_data.get(property_name, None)
        if property is None:
            raise Exception(f"{node} has no data for property {property_name}")

        return property

    def _add_property(self, node: Any, property_name: str, value: Any) -> None:
        key = node
        if isinstance(node, CLRList):
            key = node.guid

        node_data = self.nodes.get(key, None)
        if node_data is None:
            node_data = {}
            self.nodes[key] = node_data

        if node_data.get(property_name, None) is not None:
            return
            raise Exception(f"{node} already has value for property {property_name}")
        node_data[property_name] = value

    def add_propagated_type(self, asl: CLRList, type: Type):
        self._add_property(asl, "propagated_type", type)

    def add_module_of_propagated_type(self, asl: CLRList, mod: Context):
        self._add_property(asl, "module_of_propagated_type", mod)

    # get the type propagated up from this node
    def get_propagated_type(self, asl: CLRList) -> Type:
        return self._get_node_property(asl, "propagated_type")

    # get the module in which the propagated type is defined
    def get_module_of_propagated_type(self, asl: CLRList) -> Context:
        return self._get_node_property(asl, "module_of_propagated_type")

    def add_module(self, asl: CLRList, mod: Context):
        return self._add_property(asl, "module", mod)

    def get_module(self, asl: CLRList) -> Context:
        return self._get_node_property(asl, "module")

    def add_instances(self, asl: CLRList, instances: Instance | list[Instance]):
        if isinstance(instances, Instance):
            instances = [instances]
        self._add_property(asl, "instances", instances)

    def get_instances(self, asl: CLRList) -> list[Instance]:
        return self._get_node_property(asl, "instances")

    def add_typeclass(self, asl: CLRList, typeclass: TypeClass2):
        return self._add_property(asl, "typeclass", typeclass)

    def get_typeclass(self, asl: CLRList) -> TypeClass2:
        return self._get_node_property(asl, "typeclass")

