from __future__ import annotations
from typing import TYPE_CHECKING

from alpaca.concepts._nested_container import NestedContainer

if TYPE_CHECKING:
    from alpaca.concepts._type import Type

class Module(NestedContainer):
    container_names = ["type", "instance", "instance_state", "function_instance", "defined_type"]
    """a module is a hierarchical container which holds functions,
    struct/interface definitions, and other modules"""
    def _add_child(self, child: NestedContainer):
        if isinstance(child, Module):
            self.children.append(child)

    def get_defined_type(self, name: str) -> Type:
        return self.get_obj("defined_type", name)

    def add_defined_type(self, name: str, type: Type):
        self.add_obj("defined_type", name, type)
