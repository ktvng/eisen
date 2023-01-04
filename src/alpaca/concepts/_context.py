from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from alpaca.concepts._type import Type

from alpaca.concepts._nested_container import NestedContainer

class Context(NestedContainer):
    container_names = ["type", "instance", "instance_state", "nilstate", "function_instance", "reference_type"]

    def _add_child(self, child: NestedContainer):
        return

    def add_nilstate(self, name: str, value: bool):
        self.add_obj("nilstate", name, value)

    def get_nilstate(self, name: str) -> bool:
        return self.get_obj("nilstate", name)

    def add_reference_type(self, name: str, type: Type):
        self.add_obj("reference_type", name, type)

    def get_reference_type(self, name: str) -> Type:
        return self.get_obj("reference_type", name)
