from __future__ import annotations
import uuid

from typing import TYPE_CHECKING

from eisen.common.eiseninstance import EisenFunctionInstance
from eisen.validation.validate import Validate
from eisen.trace.entity import Angel, Trait
from eisen.trace.entanglement import Entanglement

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

    def update_with(self, other_memory: Memory) -> Memory:
        if other_memory.rewrites:
            return Memory(
                name=self.name,
                rewrites=other_memory.rewrites,
                impressions=other_memory.impressions.copy(),
                depth=self.depth,
                functions=other_memory.functions.copy())

        return Memory(
            name=self.name,
            rewrites=self.rewrites,
            impressions=self.impressions.union(other_memory.impressions),
            depth=self.depth,
            functions=self.functions.union(other_memory.functions))

    def with_depth(self, depth: int) -> Memory:
        return Memory(
            rewrites=self.rewrites,
            impressions=self.impressions,
            depth=depth,
            name=self.name,
            functions=self.functions)

    def for_entanglement(self, entanglement: Entanglement) -> Memory:
        """
        Filters itself to return a new memory with only impressions for the specified
        [entanglement]
        """
        return Memory(
            rewrites=self.rewrites,
            impressions=self.impressions.for_entanglement(entanglement),
            depth=self.depth,
            name=self.name,
            functions=self.functions.for_entanglement(entanglement))

    def with_entanglement(self, entanglement: Entanglement) -> Memory:
        """
        Adds an additional entanglement to each all impressions inside itself
        """
        return Memory(
            rewrites=self.rewrites,
            impressions=self.impressions.with_entanglement(entanglement),
            depth=self.depth,
            name=self.name,
            functions=self.functions.with_entanglement(entanglement))

    def not_for_entanglement(self, entanglement: Entanglement) -> Memory:
        """
        Filters itself to return a new memory with only impressions either not part of
        the provided [entanglement], or with no entanglements themselves.
        """
        return Memory(
            rewrites=self.rewrites,
            impressions=self.impressions.not_for_entanglement(entanglement),
            depth=self.depth,
            name=self.name,
            functions=self.functions.not_for_entanglement(entanglement))


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
        if self.functions: return " ".join([str(i) for i in self.functions])
        return " ".join([str(i) for i in self.impressions])

    def __eq__(self, o: Memory) -> bool:
        return (self.name == o.name
            and self.depth == o.depth
            and self.rewrites == o.rewrites
            and self.impressions == o.impressions)

    def __hash__(self) -> int:
        return hash(hash(self.name) + self.depth + int(self.rewrites) + hash(self.impressions))

class Function():
    def __init__(self, function_instance: EisenFunctionInstance, entanglement: Entanglement = None) -> None:
        self.function_instance = function_instance
        self.entanglement = entanglement

    def __hash__(self) -> int:
        return hash(self.function_instance)

    def __eq__(self, __value: Function) -> bool:
        return (self.function_instance == __value.function_instance
            and self.entanglement == __value.entanglement)

    def __str__(self) -> str:
        uid = str(self.entanglement) if self.entanglement is not None else ""
        return self.function_instance.name + f"({uid})"

    def with_entanglement(self, entanglement: Entanglement) -> Function:
        if self.entanglement is None:
            return Function(
                self.function_instance,
                entanglement)
        return Function(
            self.function_instance,
            self.entanglement.with_sub_entanglement(entanglement.uid))


class FunctionSet():
    def __init__(self) -> None:
        self._functions: list[Function] = []

    def add_function(self, obj: Function):
        # found_obj = [f for f in self._functions if f.function_instance == obj.function_instance]
        # if found_obj:
        #     self._functions.remove(found_obj[0])
        self._functions.append(obj)

    def add_from(self, other: FunctionSet):
        for i in other._functions:
            self.add_function(i)

    def union(self, other: FunctionSet) -> FunctionSet:
        new_set = FunctionSet()
        new_set._functions = self._functions.copy()
        for f in other._functions:
            new_set.add_function(f)
        return new_set

    def copy(self) -> FunctionSet:
        new_set = FunctionSet()
        new_set._functions = self._functions.copy()
        return new_set

    def with_entanglement(self, entanglement: Entanglement) -> FunctionSet:
        new_set = FunctionSet()
        for f in self._functions:
            new_set.add_function(f.with_entanglement(entanglement))
        return new_set

    def for_entanglement(self, entanglement: Entanglement) -> FunctionSet:
        new_set = FunctionSet()
        if entanglement is None:
            new_set._functions = set([f for f in self._functions])
        else:
            new_set._functions = set([f for f in self._functions if entanglement.matches(f.entanglement)])
        return new_set

    def not_for_entanglement(self, entanglement: Entanglement) -> FunctionSet:
        new_set = FunctionSet()
        new_set._functions = set([f for f in self._functions if not entanglement.matches(f.entanglement) or f.entanglement is None])
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
        self._impressions: set[Impression] = set()

    def add_impression(self, obj: Impression):
        self._impressions.add(obj)

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

    def for_entanglement(self, entanglement: Entanglement) -> ImpressionSet:
        new_set = ImpressionSet()
        if entanglement is None:
            new_set._impressions = set([i for i in self._impressions])
        else:
            new_set._impressions = set([i for i in self._impressions if entanglement.matches(i.entanglement)])
        return new_set

    def not_for_entanglement(self, entanglement: Entanglement) -> ImpressionSet:
        new_set = ImpressionSet()
        new_set._impressions = set([i for i in self._impressions if not entanglement.matches(i.entanglement) or i.entanglement is None])
        return new_set

    def with_entanglement(self, entanglement: Entanglement) -> ImpressionSet:
        new_set = ImpressionSet()
        for i in self._impressions:
            new_set.add_impression(i.with_entanglement(entanglement))
        return new_set

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
    def __init__(self, shadow: Shadow, root: Trait, place: int, entanglement: Entanglement = None) -> None:
        self.shadow = shadow
        self.root = root
        self.place = place
        self.entanglement = entanglement

    def with_entanglement(self, entanglement: Entanglement) -> Impression:
        if self.entanglement is None:
            return Impression(
                self.shadow,
                self.root,
                self.place,
                entanglement)

        return Impression(
            self.shadow,
            self.root,
            self.place,
            self.entanglement.with_sub_entanglement(entanglement.uid))

    def __str__(self) -> str:
        uid = str(self.entanglement) if self.entanglement is not None else ""
        if isinstance(self.shadow.entity, Angel):
            return str(self.shadow.entity)
        if self.root:
            return self.shadow.entity.name + "." + str(self.root)
        return self.shadow.entity.name + f"({uid})"

    def __eq__(self, o: Impression) -> bool:
        return (self.shadow == o.shadow
            and self.root == o.root
            and self.entanglement == o.entanglement)

    def __hash__(self) -> int:
        return hash(hash(self.shadow) + hash(self.root))
