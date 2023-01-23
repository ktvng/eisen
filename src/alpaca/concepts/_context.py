from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from alpaca.concepts._type import Type

from alpaca.concepts._nested_container import NestedContainer

class Context(NestedContainer):
    container_names = ["type", "instance", "instance_state", "nilstate", "function_instance", "reference_type",
    "depth", "spread", "local_ref"]

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

    def add_depth(self, name: str, value: int):
        self.add_obj("depth", name, value)

    def get_depth(self, name: str):
        return self.get_obj("depth", name)

    def add_spread(self, name: str, value: int):
        self.add_obj("spread", name, value)

    def get_spread(self, name: str):
        return self.get_obj("spread", name)

    def add_local_ref(self, name: str):
        self.add_obj("local_ref", name, True)

    def get_local_ref(self, name: str) -> bool:
        found = self.get_obj("local_ref", name)
        if found:
            return True
        return False
