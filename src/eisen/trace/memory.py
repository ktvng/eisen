from __future__ import annotations
import uuid

from typing import TYPE_CHECKING

from eisen.validation.validate import Validate
from eisen.trace.entity import Angel, Trait

if TYPE_CHECKING:
    from eisen.trace.shadow import Shadow
    from eisen.state.memoryvisitorstate import MemoryVisitorState

class Memory():
    def __init__(self, rewrites: bool, impressions: ImpressionSet, depth: int, name: str = "") -> None:
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
        impressions = ImpressionSet()
        for i in self.impressions:
            found = index.get(i.shadow.entity.uid, None)
            if found is not None:
                if isinstance(found, list):
                    for m in found:
                        impressions.add_from(m.impressions)
                else:
                    impressions.add_from(found.impressions)
            else:
                impressions.add_impression(i)
        return Memory(name=self.name, rewrites=self.rewrites, impressions=impressions, depth=self.depth)

    def validate_dependencies_outlive_self(self, state: MemoryVisitorState, memory_name: str, self_shadow: Shadow):
        for impression in self.impressions:
            Validate.dependency_outlives_self(state, memory_name, self_shadow, impression)

    def restore_to_healthy(self) -> Memory:
        impressions = ImpressionSet()
        for i in self.impressions:
            if i.shadow.entity.depth > self.depth:
                continue

            impressions.add_impression(i)
        return Memory(name=self.name, rewrites=self.rewrites, impressions=impressions, depth=self.depth)

    @staticmethod
    def merge_all(memories: list[Memory], depth: int, rewrites: bool) -> Memory:
        impressions = ImpressionSet()
        for m in memories:
            impressions.add_from(m.impressions)
        return Memory(rewrites=rewrites, impressions=impressions, depth=depth)

    def __str__(self) -> str:
        return " ".join([str(i) for i in self.impressions])

    def __eq__(self, o: Memory) -> bool:
        return (self.name == o.name
            and self.depth == o.depth
            and self.rewrites == o.rewrites
            and self.impressions == o.impressions)

    def __hash__(self) -> int:
        return hash(hash(self.name) + self.depth + int(self.rewrites) + hash(self.impressions))

class ImpressionSet():
    def __init__(self) -> None:
        self._impressions: list[Impression] = []

    def add_impression(self, obj: Impression):
        found_obj = [i for i in self._impressions if i.shadow.entity == obj.shadow.entity]
        if found_obj:
            self._impressions.remove(found_obj[0])
        self._impressions.append(obj)

    def add_from(self, other: ImpressionSet):
        for i in other._impressions:
            self.add_impression(i)

    def union(self, other: ImpressionSet) -> ImpressionSet:
        new_set = ImpressionSet()
        new_set._impressions = self._impressions.copy()
        for i in other._impressions:
            new_set.add_impression(i)
        return new_set

    def copy(self) -> ImpressionSet:
        new_set = ImpressionSet()
        new_set._impressions = self._impressions.copy()
        return new_set

    def first(self) -> Impression:
        return self._impressions[0]

    @staticmethod
    def create_over(impression: Impression | list[Impression]) -> ImpressionSet:
        new_set = ImpressionSet()
        if isinstance(impression, Impression):
            impression = [impression]
        new_set._impressions = impression.copy()
        return new_set

    def __iter__(self):
        return self._impressions.__iter__()

    def __len__(self) -> int:
        return len(self._impressions)

    def __eq__(self, __value: ImpressionSet) -> bool:
        return all(x == y for x, y in zip(self._impressions, __value._impressions))

    def __hash__(self) -> int:
        return hash(sum([hash(x) for x in self._impressions]))


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

    def __eq__(self, o: Impression) -> bool:
        return (self.shadow == o.shadow
            and self.root == o.root)

    def __hash__(self) -> int:
        return hash(hash(self.shadow) + hash(self.root))
