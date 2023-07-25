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

class Angel(Entity):
    def __init__(self, trait: Trait, entity: Entity) -> None:
        super().__init__(entity.name + "." + trait.value, entity.depth)
        self.entity = entity
        self.trait = trait

    def __str__(self) -> str:
        return f"({self.name})"

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

    def update_with(self, other: Shadow, root: Trait, depth: int) -> Shadow:
        return Shadow(entity=self.entity,
                      epoch=other.epoch,
                      faded=other.faded,
                      personality=self.personality.update_with(other.personality, root, depth))

    def update_personality(self, other_personality: Personality, root: Trait, depth: int) -> Shadow:
        return Shadow(entity=self.entity,
                      epoch=self.epoch,
                      faded=self.faded,
                      personality=self.personality.update_with(other_personality, root, depth))

    # TODO: need to validate that personality doesn't depend on higher depth
    # objects.
    def validate_dependencies_outlive_self(self, state: State):
        self.personality.validate_dependencies_outlive_self(state, self)

    def restore_to_healthy(self) -> Shadow:
        return Shadow(entity=self.entity,
                      epoch=self.epoch,
                      faded=self.faded,
                      personality=self.personality.restore_to_healthy())


    @staticmethod
    def merge_all(shadows: list[Shadow], depth: int) -> Shadow:
        return Shadow(entity=shadows[0].entity,
                            epoch=max([s.epoch for s in shadows]),
                            faded=any([s.faded for s in shadows]),
                            personality=Personality.merge_all([s.personality for s in shadows], depth))

    def __str__(self) -> str:
        return f"{self.entity.name} === \n{self.personality}"

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


class Memory():
    def __init__(self, rewrites: bool, impressions: set[Impression], depth: int, name: str = "") -> None:
        self.name = name
        self.depth = depth
        self.rewrites = rewrites
        self.impressions = impressions

    def update_with(self, other_memory: Memory, extend: bool = False) -> Memory:
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

    def validate_dependencies_outlive_self(self, state: State, memory_name: str, self_shadow: Shadow):
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
    def merge_all(memories: list[Memory], depth: int) -> Memory:
        impressions = set()
        for m in memories:
            impressions = impressions.union(m.impressions)
        return Memory(rewrites=True, impressions=impressions, depth=depth)

    def __str__(self) -> str:
        return " ".join([str(i) for i in self.impressions])


class Personality():
    def __init__(self, memories: dict[Trait, Memory]) -> None:
        self.memories = memories

    def get_memory(self, trait: Trait) -> Memory:
        return self.memories.get(trait)

    @staticmethod
    def _merge_memory_dicts(merged_memories: dict[Trait, Memory],
                            other_personality: Personality,
                            depth: int,
                            extend: bool = False,
                            root: Trait = Trait("")):

        for key, memory in other_personality.memories.items():
            key = root.join(key)
            if key in merged_memories:
                merged_memories[key] = merged_memories[key].update_with(memory, extend=extend).with_depth(depth)
            else:
                merged_memories[key] = memory.with_depth(depth)

    def remap_via_index(self, index: dict[uuid.UUID, Memory]) -> Personality:
        merged_memories: dict[Trait, Memory] = { **self.memories }
        for key, memory in self.memories.items():
                merged_memories[key] = memory.remap_via_index(index)
        return Personality(merged_memories)

    def update_with(self, other_personality: Personality, root: Trait, depth: int) -> Personality:
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
        merged_memories: dict[Trait, Memory] = {}
        for other_personality in personalities:
            Personality._merge_memory_dicts(merged_memories, other_personality, extend=True, depth=depth)
        return Personality(merged_memories)

    def __str__(self) -> str:
        s = ""
        for key, memory in self.memories.items():
            s += f"| {key}: {memory}\n"
        return s


class Lval():
    def __init__(self, name: str, memory: Memory, trait: Trait) -> None:
        self.name = name
        self.memory = memory
        self.trait = trait

class FunctionDelta():
    def __init__(self,
                 arg_shadows: list[Shadow],
                 ret_shadows: list[Shadow],
                 angels: list[Angel],
                 angel_shadows: dict[uuid.UUID, Shadow],
                 ret_memories: list[Memory]) -> None:

        self.arg_shadows = arg_shadows
        self.ret_shadows = ret_shadows
        self.angels = angels
        self.angel_shadows = angel_shadows
        self.ret_memories = ret_memories

class FunctionDB():
    def __init__(self) -> None:
        self._function_deltas: dict[str, FunctionDelta] = {}

    def add_function_delta(self, name: str, fc: FunctionDelta):
        self._function_deltas[name] = fc

    def get_function_delta(self, name: str) -> FunctionDelta:
        return self._function_deltas.get(name, None)
