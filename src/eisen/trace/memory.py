from __future__ import annotations
import uuid

from typing import TYPE_CHECKING

from eisen.common.eiseninstance import EisenFunctionInstance
from eisen.validation.validate import Validate
from eisen.trace.entity import Angel, Trait
from eisen.trace.branchedrealitytag import BranchedRealityTag

if TYPE_CHECKING:
    from eisen.trace.shadow import Shadow
    from eisen.state.memoryvisitorstate import MemoryVisitorState

class Memory():
    def __init__(self, rewrites: bool, impressions: ImpressionSet, depth: int, name: str = "",
                 functions: FunctionSet = None) -> None:
        self.name = name
        self.depth = depth
        self.rewrites = rewrites
        self.impressions = impressions
        self.functions = FunctionSet() if functions is None else functions

    def for_the_given_realities(self, tags: set[BranchedRealityTag], possible_tags: set[BranchedRealityTag] = None) -> Memory:
        if not tags:
            return self
        return Memory(
            name=self.name,
            rewrites=self.rewrites,
            impressions=self.impressions.for_the_given_realities(tags, possible_tags),
            depth=self.depth,
            functions=self.functions.for_the_given_realities(tags))

    def for_reality_of_superposition(self, tag: BranchedRealityTag) -> Memory:
        return Memory(
            name=self.name,
            rewrites=self.rewrites,
            impressions=self.impressions.for_reality_of_superposition(tag),
            depth=self.depth,
            functions=self.functions.for_reality_of_superposition(tag))

    def update_with(self, other_memory: Memory, tag: BranchedRealityTag = None) -> Memory:
        if other_memory.rewrites:
            return Memory(
                name=self.name,
                rewrites=other_memory.rewrites,
                impressions=other_memory.impressions.with_tag(tag).copy(),
                depth=self.depth,
                functions=other_memory.functions.copy())

        return Memory(
            name=self.name,
            rewrites=self.rewrites,
            impressions=self.impressions.union(other_memory.impressions.with_tag(tag)),
            depth=self.depth,
            functions=self.functions.union(other_memory.functions))

    def with_tag(self, tag: BranchedRealityTag) -> Memory:
        return Memory(
            rewrites=self.rewrites,
            impressions=self.impressions.with_tag(tag),
            depth=self.depth,
            name=self.name,
            functions=self.functions)

    def replace_base_with_tag(self, tag: BranchedRealityTag) -> Memory:
        return Memory(
            rewrites=self.rewrites,
            impressions=self.impressions.replace_base_with_tag(tag),
            depth=self.depth,
            name=self.name,
            functions=self.functions)

    def with_depth(self, depth: int) -> Memory:
        return Memory(
            rewrites=self.rewrites,
            impressions=self.impressions,
            depth=depth,
            name=self.name,
            functions=self.functions)

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
        return Memory(
            name=self.name,
            rewrites=self.rewrites,
            impressions=impressions,
            depth=self.depth,
            functions=self.functions)

    def validate_dependencies_outlive_self(self, state: MemoryVisitorState, memory_name: str, self_shadow: Shadow):
        for impression in self.impressions:
            Validate.dependency_outlives_self(state, memory_name, self_shadow, impression)

    def restore_to_healthy(self) -> Memory:
        impressions = ImpressionSet()
        for i in self.impressions:
            if i.shadow.entity.depth > self.depth:
                continue

            impressions.add_impression(i)
        return Memory(name=self.name,
                      rewrites=self.rewrites,
                      impressions=impressions,
                      depth=self.depth,
                      functions=self.functions)

    @staticmethod
    def merge_all(memories: list[Memory], rewrites: bool) -> Memory:
        impressions = ImpressionSet()
        functions = FunctionSet()
        for m in memories:
            impressions.add_from(m.impressions)
            functions.add_from(m.functions)
        return Memory(
            rewrites=rewrites,
            impressions=impressions,
            depth=memories[0].depth,
            functions=functions)

    def __str__(self) -> str:
        return " ".join([str(i) for i in self.impressions])

    def __eq__(self, o: Memory) -> bool:
        return (self.name == o.name
            and self.depth == o.depth
            and self.rewrites == o.rewrites
            and self.impressions == o.impressions)

    def __hash__(self) -> int:
        return hash(hash(self.name) + self.depth + int(self.rewrites) + hash(self.impressions))

class Function():
    def __init__(self, function_instance: EisenFunctionInstance,
                 tags: set[BranchedRealityTag]) -> None:
        self.function_instance = function_instance
        self.tags = tags

    def __hash__(self) -> int:
        return hash(self.function_instance)

    def __eq__(self, __value: Function) -> bool:
        return self.function_instance == __value.function_instance

    def with_additional_tags(self, tags: set[BranchedRealityTag]) -> Function:
        return Function(function_instance=self.function_instance, tags = self.tags.union(tags))

    @staticmethod
    def for_the_given_realities(tags: set[BranchedRealityTag], fns: set[Function]) -> set[Function]:
        return set([f for f in fns if any(tag and tag.symbiotic_with_any(tags) for tag in f.tags)])

    @staticmethod
    def for_reality_of_superposition(tag: BranchedRealityTag, fns: set[Function]) -> set[Function]:
        return Function.for_the_given_realities([tag], fns)

class FunctionSet():
    def __init__(self) -> None:
        self._functions: list[Function] = []

    def add_function(self, obj: Function):
        found_obj = [f for f in self._functions if f.function_instance == obj.function_instance]
        tags = set()
        if found_obj:
            self._functions.remove(found_obj[0])
            tags = found_obj[0].tags
        self._functions.append(obj.with_additional_tags(tags))

    def add_from(self, other: FunctionSet):
        for i in other._functions:
            self.add_function(i)

    def union(self, other: FunctionSet) -> FunctionSet:
        new_set = FunctionSet()
        new_set._functions = self._functions.copy()
        for f in other._functions:
            new_set.add_function(f)
        return new_set

    def for_the_given_realities(self, tags: set[BranchedRealityTag]) -> FunctionSet:
        fns = [f for f in self._functions if any(tag and tag.symbiotic_with_any(tags) for tag in f.tags)]
        new_set = FunctionSet()
        new_set._functions = fns
        return new_set

    def copy(self) -> FunctionSet:
        new_set = FunctionSet()
        new_set._functions = self._functions.copy()
        return new_set

    @staticmethod
    def create_over(function: Function | list[Function]) -> FunctionSet:
        new_set = FunctionSet()
        if isinstance(function, Function):
            function = [function]
        new_set._functions = function.copy()
        return new_set

    def __iter__(self):
        return self._functions.__iter__()

    def __len__(self) -> int:
        return len(self._functions)

class ImpressionSet():
    def __init__(self) -> None:
        self._impressions: list[Impression] = []

    def add_impression(self, obj: Impression):
        found_obj = [i for i in self._impressions if i.shadow.entity == obj.shadow.entity]
        tags = set()
        if found_obj:
            self._impressions.remove(found_obj[0])
            tags = found_obj[0].tags
        self._impressions.append(obj.with_additional_tags(tags))

    def replace_base_with_tag(self, tag: BranchedRealityTag) -> ImpressionSet:
        new_set = ImpressionSet()
        new_set._impressions = [i.with_tag(tag) if len(i.tags) == 1 and next(iter(i.tags)).is_from_base_branch()
                                else i for i in self._impressions]
        return new_set

    def with_tag(self, tag: BranchedRealityTag) -> ImpressionSet:
        if tag is None:
            return self
        new_set = ImpressionSet()
        new_set._impressions = [i.with_tag(tag) for i in self._impressions]
        return new_set

    def for_the_given_realities(self, tags: set[BranchedRealityTag], possible_tags: set[BranchedRealityTag]) -> ImpressionSet:
        # TODO: formalize this hotfix
        if len(tags) == 1 and uuid.UUID(int=0) in [tag.uid for tag in tags]:
            if possible_tags is None:
                imps = self._impressions
            elif len(possible_tags) == 0:
                imps = self._impressions
            else:
                possible_tags = possible_tags.copy()
                possible_tags.remove(BranchedRealityTag(uuid.UUID(int=0), 0))
                imps = [i for i in self._impressions if any(tag not in possible_tags for tag in i.tags)]
            new_set = ImpressionSet()
            new_set._impressions = imps
            return new_set

        new_set = ImpressionSet()
        new_set._impressions = [i for i in self._impressions if any(tag and tag.symbiotic_with_any(tags) for tag in i.tags)]
        if not new_set._impressions:
            new_set._impressions = [i for i in self._impressions if any(tag.is_from_base_branch() for tag in i.tags)]
        return new_set

    def for_reality_of_superposition(self, tag: BranchedRealityTag) -> ImpressionSet:
        return self.for_the_given_realities([tag], None)

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
    def __init__(self, shadow: Shadow, root: Trait, place: int, tags: set[BranchedRealityTag]) -> None:
        self.shadow = shadow
        self.root = root
        self.place = place
        self.tags = tags

    def with_tag(self, tag: BranchedRealityTag) -> Impression:
        return Impression(
            self.shadow,
            self.root,
            self.place,
            set([tag]))

    def with_additional_tags(self, tags: set[BranchedRealityTag]) -> Impression:
        return Impression(
            self.shadow,
            self.root,
            self.place,
            self.tags.union(tags)
        )

    def __str__(self) -> str:
        tags = ""
        if self.tags:
            tags = f"({', '.join(str(t.uid)[0:5] + '.' + str(t.branch_number) for t in self.tags)})"
        if isinstance(self.shadow.entity, Angel):
            return str(self.shadow.entity) + tags
        if self.root:
            return self.shadow.entity.name + "." + str(self.root) + tags
        return self.shadow.entity.name + tags

    def __eq__(self, o: Impression) -> bool:
        return (self.shadow == o.shadow
            and self.root == o.root)

    def __hash__(self) -> int:
        return hash(hash(self.shadow) + hash(self.root))
