from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from alpaca.concepts._type import Type
    import uuid

from alpaca.concepts._nested_container import NestedContainer

class Context(NestedContainer):
    container_names = ["type", "instance", "binding_condition", "nilstatus",
                       "function_instance", "reference_type",
                       "local_ref", "entity", "entity_uuids",
                       "memory", "shadow", "entity"]

    def _add_child(self, child: NestedContainer):
        return

    def add_nilstatus(self, name: str, value: Any):
        self.add_obj("nilstatus", name, value)

    def get_nilstatus(self, name: str) -> Any:
        return self.get_obj("nilstatus", name)

    def get_all_local_nilstatuses(self):
        return self.get_all_local_objs("nilstatus")

    def add_type_of_reference(self, reference_name: str, type: Type):
        self.add_obj("reference_type", reference_name, type)

    def get_type_of_reference(self, name: str) -> Type:
        return self.get_obj("reference_type", name)

    def add_local_ref(self, name: str):
        self.add_obj("local_ref", name, True)

    def get_local_ref(self, name: str) -> bool:
        found = self.get_obj("local_ref", name)
        if found:
            return True
        return False

    def get_entity(self, uid: uuid.UUID):
        return self.get_obj("entity", uid)

    def add_entity(self, uid: uuid.UUID, value: Any):
        self.add_obj("entity", uid, value)
