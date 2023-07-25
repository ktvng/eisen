from __future__ import annotations
import uuid

from typing import TYPE_CHECKING

from eisen.validation.validate import Validate
from eisen.trace.entity import Angel, Trait

if TYPE_CHECKING:
    from eisen.trace.shadow import Shadow
    from eisen.state.memoryvisitorstate import MemoryVisitorState

class Memory():
    def __init__(self, rewrites: bool, impressions: set[Impression], depth: int, name: str = "") -> None:
        self.name = name
        self.depth = depth
        self.rewrites = rewrites
        self.impressions = impressions

    def update_with(self, other_memory: Memory) -> Memory:
        if other_memory.rewrites:
            return Memory(
                name=self.name,
                rewrites=other_memory.rewrites,
                impressions=other_memory.impressions.copy(),
                depth=self.depth)

        return Memory(
            name=self.name,
            rewrites=self.rewrites,
            impressions=self.impressions.union(other_memory.impressions),
            depth=self.depth)

    def with_depth(self, depth: int) -> Memory:
        return Memory(self.rewrites, self.impressions, depth, name=self.name)

    def remap_via_index(self, index: dict[uuid.UUID, Memory]) -> Memory:
        impressions = []
        for i in self.impressions:
            found = index.get(i.shadow.entity.uid, None)
            if found is not None:
                if isinstance(found, list):
                    for m in found:
                        impressions += m.impressions
                else:
                    impressions += found.impressions
            else:
                impressions.append(i)
        return Memory(name=self.name, rewrites=self.rewrites, impressions=set(impressions), depth=self.depth)

    def validate_dependencies_outlive_self(self, state: MemoryVisitorState, memory_name: str, self_shadow: Shadow):
        for impression in self.impressions:
            Validate.dependency_outlives_self(state, memory_name, self_shadow, impression)

    def restore_to_healthy(self) -> Memory:
        impressions = []
        for i in self.impressions:
            if i.shadow.entity.depth > self.depth:
                continue

            impressions.append(i)
        return Memory(name=self.name, rewrites=self.rewrites, impressions=set(impressions), depth=self.depth)

    @staticmethod
    def merge_all(memories: list[Memory], depth: int, rewrites: bool) -> Memory:
        impressions = set()
        for m in memories:
            impressions = impressions.union(m.impressions)
        return Memory(rewrites=rewrites, impressions=impressions, depth=depth)

    def __str__(self) -> str:
        return " ".join([str(i) for i in self.impressions])

    def __eq__(self, o: Memory) -> bool:
        return (self.name == o.name
            and self.depth == o.depth
            and self.rewrites == o.rewrites
            and self.impressions == o.impressions)

    def __hash__(self) -> int:
        return hash(self.name + str(self.depth))

class Impression():
    def __init__(self, shadow: Shadow, root: Trait, place: int) -> None:
        self.shadow = shadow
        self.root = root
        self.place = place

    def __str__(self) -> str:
        if isinstance(self.shadow.entity, Angel):
            return str(self.shadow.entity)
        if self.root:
            return self.shadow.entity.name + "." + str(self.root)
        return self.shadow.entity.name
