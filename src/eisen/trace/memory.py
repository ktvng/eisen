from __future__ import annotations
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from eisen.validation.validate import Validate
from eisen.trace.entity import Angel, Trait
from eisen.trace.entanglement import Entanglement

if TYPE_CHECKING:
    from eisen.trace.shadow import Shadow
    from eisen.state.memoryvisitorstate import MemoryVisitorState

class Memory():
    __slots__ = ('name', 'depth', 'rewrites', 'impressions')

    def __init__(self, rewrites: bool, depth: int, name: str = "",
                 impressions: MemorableSet = None):
        self.name = name
        self.depth = depth
        self.rewrites = rewrites
        self.impressions = MemorableSet() if impressions is None else impressions

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

    def update_to_latest(self, state: MemoryVisitorState) -> Memory:
        return Memory(
            name=self.name,
            rewrites=self.rewrites,
            impressions=self.impressions.update_to_latest(state),
            depth=self.depth)

    def with_depth(self, depth: int) -> Memory:
        return Memory(
            rewrites=self.rewrites,
            impressions=self.impressions,
            depth=depth,
            name=self.name)

    def for_entanglement(self, entanglement: Entanglement) -> Memory:
        """
        Filters itself to return a new memory with only impressions for the specified
        [entanglement]
        """
        return Memory(
            rewrites=self.rewrites,
            impressions=self.impressions.for_entanglement(entanglement),
            depth=self.depth,
            name=self.name)

    def with_entanglement(self, entanglement: Entanglement) -> Memory:
        """
        Adds an additional entanglement to each all impressions inside itself
        """
        return Memory(
            rewrites=self.rewrites,
            impressions=self.impressions.with_entanglement(entanglement),
            depth=self.depth,
            name=self.name)

    def not_for_entanglement(self, entanglement: Entanglement) -> Memory:
        """
        Filters itself to return a new memory with only impressions either not part of
        the provided [entanglement], or with no entanglements themselves.
        """
        return Memory(
            rewrites=self.rewrites,
            impressions=self.impressions.not_for_entanglement(entanglement),
            depth=self.depth,
            name=self.name)

    def remap_via_index(self, index: dict[uuid.UUID, Memory]) -> Memory:
        impressions = MemorableSet()
        for i in self.impressions:
            found = index.get(i.shadow.entity.uid, None)
            if found is not None:
                if isinstance(found, list):
                    for m in found:
                        impressions.add_from(m.impressions)
                else:
                    impressions.add_from(found.impressions)
            else:
                impressions.add(i)
        return Memory(
            name=self.name,
            rewrites=self.rewrites,
            impressions=impressions,
            depth=self.depth)

    def validate_dependencies_outlive_self(self, state: MemoryVisitorState, memory_name: str, self_shadow: Shadow):
        for impression in self.impressions:
            Validate.dependency_outlives_self(state, memory_name, self_shadow, impression)

    def restore_to_healthy(self) -> Memory:
        impressions = MemorableSet()
        for i in self.impressions:
            if i.shadow.entity.depth > self.depth:
                continue

            impressions.add(i)
        return Memory(name=self.name,
                      rewrites=self.rewrites,
                      impressions=impressions,
                      depth=self.depth)

    @staticmethod
    def merge_all(memories: list[Memory], rewrites: bool) -> Memory:
        impressions = MemorableSet()
        for m in memories:
            impressions.add_from(m.impressions)
        return Memory(
            rewrites=rewrites,
            impressions=impressions,
            depth=memories[0].depth)

    @staticmethod
    def get_identity_memory() -> Memory:
        return Memory(rewrites=False, depth=0)

    def __str__(self) -> str:
        return " ".join([str(i) for i in self.impressions])

    def __eq__(self, o: Memory) -> bool:
        return (self.name == o.name
            and self.depth == o.depth
            and self.rewrites == o.rewrites
            and self.impressions == o.impressions)

    def __hash__(self) -> int:
        return hash(hash(self.name) + self.depth + int(self.rewrites) + hash(self.impressions))

class MemorableSet():
    def __init__(self, objs: set[Impression] = None) -> None:
        self.objs = objs if objs else set()

    def add(self, obj: Impression):
        self.objs.add(obj)

    def add_from(self, other: MemorableSet):
        for i in other.objs:
            self.add(i)

    def union(self, other: MemorableSet) -> MemorableSet:
        return MemorableSet(self.objs.union(other.objs))

    def copy(self) -> MemorableSet:
        return MemorableSet(self.objs.copy())

    def with_entanglement(self, entanglement: Entanglement) -> MemorableSet:
        return MemorableSet(set([obj.with_entanglement(entanglement) for obj in self.objs]))

    def for_entanglement(self, entanglement: Entanglement) -> MemorableSet:
        if entanglement is None: return self
        return MemorableSet(set([o for o in self.objs if entanglement.matches(o.entanglement)]))

    def not_for_entanglement(self, entanglement: Entanglement) -> MemorableSet:
        return MemorableSet(set([o for o in self.objs
            if not entanglement.matches(o.entanglement) or o.entanglement is None]))

    def update_to_latest(self, state: MemoryVisitorState) -> MemorableSet:
        return MemorableSet(set([o.update_to_latest(state) for o in self.objs]))

    def first(self) -> Impression:
        return next(iter(self.objs))

    def __iter__(self):
        return self.objs.__iter__()

    def __len__(self) -> int:
        return len(self.objs)

    def __eq__(self, __value: MemorableSet) -> bool:
        return all(x == y for x, y in zip(self.objs, __value.objs))

    def __hash__(self) -> int:
        return hash(sum([hash(x) for x in self.objs]))

    def get_shadows(self) -> list[Shadow]:
        return [i.shadow for i in self.objs]

    @staticmethod
    def create_over(obj) -> MemorableSet:
        if not isinstance(obj, list):
            obj = [obj]
        return MemorableSet(set(obj))
@dataclass
class Impression():
    shadow: Shadow
    root: Trait
    entanglement: Entanglement | None = None

    def with_entanglement(self, entanglement: Entanglement) -> Impression:
        if self.entanglement is None:
            return Impression(
                self.shadow,
                self.root,
                entanglement)

        return Impression(
            self.shadow,
            self.root,
            self.entanglement.with_sub_entanglement(entanglement.uid))

    def update_to_latest(self, state: MemoryVisitorState) -> Impression:
        return Impression(
            shadow=state.get_shadow(self.shadow.entity),
            root=self.root,
            entanglement=self.entanglement)

    def __str__(self) -> str:
        uid = f"<{str(self.entanglement)}>" if self.entanglement is not None else ""
        if isinstance(self.shadow.entity, Angel):
            return str(self.shadow.entity) + uid
        if self.root:
            return self.shadow.entity.name + "." + str(self.root)
        return self.shadow.entity.name + uid

    def __eq__(self, o: Impression) -> bool:
        return (self.shadow == o.shadow
            and self.root == o.root
            and self.entanglement == o.entanglement)

    def __hash__(self) -> int:
        return hash(hash(self.shadow) + hash(self.root))
