from __future__ import annotations
import uuid

from eisen.state.basestate import BaseState
from eisen.validation.validate import Validate

State = BaseState

class Entity():
    def __init__(self, name: str, depth: int) -> None:
        self.name = name
        self.depth = depth
        self.uid = uuid.uuid4()

    def __str__(self) -> str:
        return f"{self.name}"

class Angel(Entity):
    def __init__(self, entity_attribute: str, entity: Entity) -> None:
        super().__init__(entity_attribute, entity.depth)
        self.entity = entity
        self.entity_attribute = entity_attribute
        self.uid = uuid.uuid4()

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

    def update_with(self, other: Shadow, root: str) -> Shadow:
        return Shadow(entity=self.entity,
                      epoch=other.epoch,
                      faded=other.faded,
                      personality=self.personality.update_with(other.personality, root))

    def update_personality(self, other_personality: Personality) -> Shadow:
        return Shadow(entity=self.entity,
                      epoch=self.epoch,
                      faded=self.faded,
                      personality=self.personality.update_with(other_personality, ""))

    # TODO: need to validate that personality doesn't depend on higher depth
    # objects.
    def validate_dependencies_outlive_self(self, state: State):
        self.personality.validate_dependencies_outlive_self(state, self)

    @staticmethod
    def merge_all(shadows: list[Shadow]) -> Shadow:
        return Shadow(entity=shadows[0].entity,
                            epoch=max([s.epoch for s in shadows]),
                            faded=any([s.faded for s in shadows]),
                            personality=Personality.merge_all([s.personality for s in shadows]))

    def __str__(self) -> str:
        return f"{self.entity.name} === \n{self.personality}"

class Impression():
    def __init__(self, shadow: Shadow, trait: str, place: int) -> None:
        self.shadow = shadow
        self.trait = trait
        self.place = place




class Memory():
    def __init__(self, rewrites: bool, shadows: set[Shadow]) -> None:
        self.rewrites = rewrites
        self.shadows = shadows

    def update_with(self, other_memory: Memory, extend: bool = False) -> Memory:
        if not extend:
            return Memory(rewrites=self.rewrites, shadows=other_memory.shadows.copy())
        return Memory(rewrites=self.rewrites, shadows=self.shadows.union(other_memory.shadows))

    def remap_via_index(self, index: dict[uuid.UUID, Memory]):
        shadows = []
        for s in self.shadows:
            found = index.get(s.entity.uid, None)
            if found is not None:
                shadows += found.shadows
            else:
                shadows.append(s)
        return Memory(rewrites=self.rewrites, shadows=set(shadows))

    def validate_dependencies_outlive_self(self, state: State, memory_name: str, self_shadow: Shadow):
        for shadow in self.shadows:
            Validate.dependency_outlives_self(state, memory_name, self_shadow, shadow)


    @staticmethod
    def merge_all(memories: list[Memory]) -> Memory:
        shadows = set()
        for m in memories:
            shadows = shadows.union(m.shadows)
        return Memory(rewrites=True, shadows=shadows)

    def __str__(self) -> str:
        return " ".join([s.entity.name for s in self.shadows])


class Personality():
    def __init__(self, memories: dict[str, Memory]) -> None:
        self.memories = memories

    def get_memory(self, trait: str) -> Memory:
        return self.memories.get(trait)

    @staticmethod
    def _merge_memory_dicts(merged_memories: dict[str, Memory],
                            other_personality: Personality,
                            extend: bool = False,
                            root: str = ""):

        for key, memory in other_personality.memories.items():
            key = root + "." + key if root else key
            if key in merged_memories:
                merged_memories[key] = merged_memories[key].update_with(memory, extend=extend)
            else:
                merged_memories[key] = memory

    def remap_via_index(self, index: dict[uuid.UUID, Memory]) -> Personality:
        merged_memories: dict[str, Memory] = { **self.memories }
        for key, memory in self.memories.items():
                merged_memories[key] = memory.remap_via_index(index)
        return Personality(merged_memories)

    def update_with(self, other_personality: Personality, root: str) -> Personality:
        merged_memories: dict[str, Memory] = { **self.memories }
        Personality._merge_memory_dicts(merged_memories, other_personality, root=root)
        return Personality(merged_memories)

    def validate_dependencies_outlive_self(self, state: State, self_shadow: Shadow):
        for name, memory in self.memories.items():
            memory.validate_dependencies_outlive_self(state, name, self_shadow)

    @staticmethod
    def merge_all(personalities: list[Personality]) -> Personality:
        merged_memories: dict[str, Memory] = {}
        for other_personality in personalities:
            Personality._merge_memory_dicts(merged_memories, other_personality, extend=True)
        return Personality(merged_memories)

    def __str__(self) -> str:
        s = ""
        for key, memory in self.memories.items():
            s += f"| {key}: {memory}\n"
        return s


class Lval():
    def __init__(self, name: str, memory: Memory, trait: str) -> None:
        self.name = name
        self.memory = memory
        self.trait = trait

class FunctionDelta():
    def __init__(self,
                 arg_shadows: list[Shadow],
                 ret_shadows: list[Shadow]) -> None:
        self.arg_shadows = arg_shadows
        self.ret_shadows = ret_shadows

class FunctionDB():
    def __init__(self) -> None:
        self._function_deltas: dict[str, FunctionDelta] = {}

    def add_function_delta(self, name: str, fc: FunctionDelta):
        self._function_deltas[name] = fc

    def get_function_delta(self, name: str) -> FunctionDelta:
        return self._function_deltas.get(name, None)
