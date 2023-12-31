from __future__ import annotations
import uuid

from eisen.state.basestate import BaseState

State = BaseState

class Entity():
    def __init__(self, name: str, depth: int) -> None:
        self.name = name
        self.depth = depth
        self.moved = False
        self.uid = uuid.uuid4()

    def __str__(self) -> str:
        return f"{self.name}"

class Trait():
    def __init__(self, value: str = "") -> None:
        self.value = value

    def __len__(self) -> int:
        return len(self.value)

    def join(self, o: Trait) -> Trait:
        if not self:
            return o
        if not o:
            return self
        return Trait(self.value + "." + o.value)

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, __value: object) -> bool:
        return self.value == __value.value

    def __str__(self) -> str:
        return self.value

    def __lt__(self, other) -> bool:
        return self.value < other.value

class Angel(Entity):
    def __init__(self, trait: Trait, entity: Entity) -> None:
        super().__init__(entity.name + "." + trait.value, entity.depth)
        self.entity = entity
        self.trait = trait

    def __str__(self) -> str:
        return f"({self.name})"

    def get_guardian_entity(self) -> Entity:
        return self.entity
