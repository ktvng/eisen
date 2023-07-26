from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from alpaca.concepts._type import Type
    import uuid

from alpaca.concepts._nested_container import NestedContainer

class Context(NestedContainer):
    container_names = ["type", "instance", "instance_state", "nilstatus", "function_instance", "reference_type",
    "depth", "spread", "local_ref", "fn_aliases", "entity", "entity_uuids",
    "memory", "shadow", "entity", "function_memory"]

    def _add_child(self, child: NestedContainer):
        return

    def add_nilstatus(self, name: str, value: Any):
        self.add_obj("nilstatus", name, value)

    def get_nilstatus(self, name: str) -> Any:
        return self.get_obj("nilstatus", name)

    def get_all_local_nilstatuses(self):
        return self.get_all_local_objs("nilstatus")

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

    def get_fn_alias(self, name: str):
        return self.get_obj("fn_aliases", name)

    def add_fn_alias(self, name: str, value):
        self.add_obj("fn_aliases", name, value)

    def get_entity(self, uid: uuid.UUID):
        return self.get_obj("entity", uid)

    def add_entity(self, uid: uuid.UUID, value: Any):
        self.add_obj("entity", uid, value)

    def add_entity_uuid(self, name: str, value: uuid.UUID):
        self.add_obj("entity_uuids", name, value)

    def get_entity_uuid(self, name: str) -> uuid.UUID:
        return self.get_obj("entity_uuids", name)
