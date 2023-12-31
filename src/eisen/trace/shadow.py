from __future__ import annotations
from typing import TYPE_CHECKING
from dataclasses import dataclass, field
import uuid

from eisen.common.eiseninstance import EisenFunctionInstance
from eisen.trace.entity import Trait
from eisen.trace.memory import Memory
from eisen.trace.entity import Entity
if TYPE_CHECKING:
    from eisen.state.memoryvisitorstate import MemoryVisitorState
    State = MemoryVisitorState

@dataclass(kw_only=True)
class Shadow():
    entity: Entity
    personality: Personality = field(default_factory=lambda: Personality(memories={}))
    function_instances: list[EisenFunctionInstance] = field(default_factory=list)

    def remap_via_index(self, index: dict[uuid.UUID, Memory]) -> Shadow:
        return Shadow(entity=self.entity,
                      function_instances=self.function_instances,
                      personality=self.personality.remap_via_index(index))

    def update_with(self, other: Shadow, root: Trait, depth: int) -> Shadow:
        return Shadow(entity=self.entity,
                      function_instances=self.function_instances + other.function_instances,
                      personality=self.personality.update_with(other.personality, root, depth))

    def update_personality(self, other_personality: Personality, root: Trait,) -> Shadow:
        return Shadow(entity=self.entity,
                      function_instances=self.function_instances,
                      personality=self.personality.update_with(
                          other_personality,
                          root,
                          depth=self.entity.depth))

    def validate_dependencies_outlive_self(self, state: MemoryVisitorState):
        self.personality.validate_dependencies_outlive_self(state, self)

    def restore_to_healthy(self) -> Shadow:
        return Shadow(entity=self.entity,
                      function_instances=self.function_instances,
                      personality=self.personality.restore_to_healthy())

    @staticmethod
    def merge_all(shadows: list[Shadow]) -> Shadow:
        return Shadow(
            entity=shadows[0].entity,
            function_instances=[instance for shadow in shadows for instance in shadow.function_instances],
            personality=Personality.merge_all([s.personality for s in shadows]))

    def __str__(self) -> str:
        return f"{self.entity.name} === \n{self.personality}"

    def __hash__(self) -> int:
        return hash(hash(self.entity) + hash(self.personality))

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

    def as_curried_params(self) -> list[Memory]:
        """
        Get the stored memories (in personality) as an ordered list based on the order that they were
        curried. This relies on the precondition that curried parameters stored with the trait being
        the order that they were added.
        """
        return [val for _, val in sorted(self.memories.items())]

    @staticmethod
    def merge_all(personalities: list[Personality]) -> Personality:
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
