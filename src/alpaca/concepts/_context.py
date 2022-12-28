from __future__ import annotations
from alpaca.concepts._nested_container import NestedContainer

class Context(NestedContainer):
    container_names = ["type", "instance", "instance_state", "nilstate", "function_instance"]

    def _add_child(self, child: NestedContainer):
        return

    def add_nilstate(self, name: str, value: bool):
        self.add_obj("nilstate", name, value)

    def get_nilstatate(self, name: str) -> bool:
        return self.get_obj("nilstate", name)