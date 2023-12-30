from __future__ import annotations
from typing import TYPE_CHECKING

import uuid

from eisen.trace.entity import Trait
from eisen.trace.memory import Memory
if TYPE_CHECKING:
    from eisen.trace.entity import Entity
    from eisen.state.memoryvisitorstate import MemoryVisitorState
    State = MemoryVisitorState

class Shadow():
    def __init__(self,
                 entity: Entity,
                 epoch: int,
                 faded: bool,
                 personality: Personality) -> None:
        self.entity = entity
        self.epoch = epoch
        self.faded = faded
        self.personality = personality

    def remap_via_index(self, index: dict[uuid.UUID, Memory]) -> Shadow:
        return Shadow(entity=self.entity,
                      epoch=self.epoch,
                      faded=self.faded,
                      personality=self.personality.remap_via_index(index))

    def update_with(self,
            other: Shadow,
            root: Trait,
            depth: int) -> Shadow:

        return Shadow(entity=self.entity,
                      epoch=other.epoch,
                      faded=other.faded,
                      personality=self.personality.update_with(other.personality, root, depth))

    def update_personality(self,
                other_personality: Personality,
                root: Trait,) -> Shadow:

        return Shadow(entity=self.entity,
                      epoch=self.epoch,
                      faded=self.faded,
                      personality=self.personality.update_with(other_personality, root, depth=self.entity.depth))

    # TODO: need to validate that personality doesn't depend on higher depth
    # objects.
    def validate_dependencies_outlive_self(self, state: MemoryVisitorState):
        self.personality.validate_dependencies_outlive_self(state, self)

    def restore_to_healthy(self) -> Shadow:
        return Shadow(entity=self.entity,
                      epoch=self.epoch,
                      faded=self.faded,
                      personality=self.personality.restore_to_healthy())

    @staticmethod
    def merge_all(shadows: list[Shadow]) -> Shadow:
        return Shadow(
            entity=shadows[0].entity,
            epoch=max([s.epoch for s in shadows]),
            faded=any([s.faded for s in shadows]),
            personality=Personality.merge_all([s.personality for s in shadows], shadows[0].entity.depth))

    def __str__(self) -> str:
        return f"{self.entity.name} === \n{self.personality}"



class Personality():
    def __init__(self, memories: dict[Trait, Memory]) -> None:
        self.memories = memories

    def get_memory(self, trait: Trait) -> Memory:
        return self.memories.get(trait)

    @staticmethod
    def _merge_memory_dicts(merged_memories: dict[Trait, Memory],
                            other_personality: Personality,
                            depth: int,
                            root: Trait = Trait("")):

        for key, memory in other_personality.memories.items():
            key = root.join(key)
            if key in merged_memories:
                merged_memories[key] = merged_memories[key].update_with(
                    memory).with_depth(depth)
            else:
                merged_memories[key] = memory.with_depth(depth)

    def remap_via_index(self, index: dict[uuid.UUID, Memory]) -> Personality:
        merged_memories: dict[Trait, Memory] = { **self.memories }
        for key, memory in self.memories.items():
                merged_memories[key] = memory.remap_via_index(index)
        return Personality(merged_memories)

    def update_with(self,
            other_personality: Personality,
            root: Trait,
            depth: int) -> Personality:

        merged_memories: dict[Trait, Memory] = { **self.memories }
        Personality._merge_memory_dicts(merged_memories, other_personality, root=root, depth=depth)
        return Personality(merged_memories)

    def restore_to_healthy(self) -> Personality:
        merged_memories: dict[Trait, Memory] = {}
        for key, value in self.memories.items():
            merged_memories[key] = value.restore_to_healthy()
        return Personality(merged_memories)

    def validate_dependencies_outlive_self(self, state: State, self_shadow: Shadow):
        for name, memory in self.memories.items():
            memory.validate_dependencies_outlive_self(state, name, self_shadow)

    @staticmethod
    def merge_all(personalities: list[Personality], depth: int) -> Personality:
        all_traits: set[Trait] = set()
        for p in personalities:
            all_traits = all_traits.union(set(p.memories.keys()))

        merged_memories: dict[Trait, Memory] = {}
        for trait in all_traits:
            memories_for_trait = [p.get_memory(trait) for p in personalities if p.get_memory(trait) is not None]
            merged_memories[trait] = Memory.merge_all(memories_for_trait, rewrites=True)

        return Personality(merged_memories)

    def __str__(self) -> str:
        s = ""
        for key, memory in self.memories.items():
            s += f"| {key}: {memory}\n"
        return s
