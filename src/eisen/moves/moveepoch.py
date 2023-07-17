from __future__ import annotations

import uuid
from dataclasses import dataclass

from eisen.common.eiseninstance import EisenInstance

@dataclass
class Entity:
    dependencies: set[Dependency]
    lifetime: Lifetime
    name: str = None
    uid: uuid.UUID = uuid.UUID(int=0)
    is_let: bool = False
    moved_away: bool = False

    def __str__(self) -> str:
        return f"{self.name}: {self.uid}   ... {[str(d.uid) for d in self.dependencies]}"

    @staticmethod
    def create_anonymous():
        return Entity(dependencies=set(), lifetime=Lifetime.primitive(), uid=uuid.UUID(int=0))

    def increment_generation(self):
        self.lifetime.generation += 1

    def mark_as_gone(self):
        self.moved_away = True

    def add_dependencies_on(self, other_entities: list[Entity]) -> Entity:
        new_entity = self.copy()

        if not isinstance(others, list): others = [others]
        for each_entity in other_entities:
            new_entity.dependencies.add(each_entity.as_a_dependency())
        return new_entity

    def merge_dependencies_of(self, others: list[Entity]) -> Entity:
        new_entity = self.copy()

        if not isinstance(others, list): others = [others]
        # new_entity.dependencies = self.dependencies.copy()
        for other_entity in others:
            for dependency in other_entity.dependencies:
                new_entity.dependencies.add(dependency)
        return new_entity

    def change_dependency_to(self, some_other_entity: Entity) -> Entity:
        new_entity = self.copy()
        new_entity.dependencies = set([some_other_entity.as_a_dependency()])
        return new_entity

    def take_dependencies_of(self, some_other_entity: Entity) -> Entity:
        new_entity = self.copy()
        new_entity.dependencies = some_other_entity.dependencies.copy()
        return new_entity

    def copy(self) -> Entity:
        return Entity(
            dependencies=self.dependencies.copy(),
            lifetime=self.lifetime,
            name=self.name,
            uid=self.uid,
            is_let=self.is_let,
            moved_away=self.moved_away)

    def as_a_dependency(self) -> Dependency:
        return Dependency(self.uid, self.lifetime.generation)

    @staticmethod
    def dependency_is_expired(dependency: Dependency, on_entity: Entity):
        return dependency.generation != on_entity.lifetime.generation

varieties = ["arg", "ret", "local", "primitive", "transient"]
@dataclass
class Lifetime:
    variety: str
    depth: int = 0
    generation: int = 0

    @staticmethod
    def local(depth: int) -> Lifetime:
        return Lifetime(variety="local", depth=depth)

    @staticmethod
    def primitive() -> Lifetime:
        return Lifetime(variety="primitive")

    @staticmethod
    def arg() -> Lifetime:
        return Lifetime(variety="arg")

    @staticmethod
    def ret() -> Lifetime:
        return Lifetime(variety="ret")

    @staticmethod
    def transient() -> Lifetime:
        return Lifetime(variety="transient")

    def is_ret(self) -> bool:
        return self.variety == "ret"

    def is_arg(self) -> bool:
        return self.variety == "arg"

    def is_local(self) -> bool:
        return self.variety == "local"

    def longer_than(self, other: Lifetime):
        return self.depth < other.depth

@dataclass
class Dependency:
    uid: uuid.UUID
    generation: int

    def __hash__(self) -> int:
        return hash(self.uid)

@dataclass
class LvalIdentity:
    entity: Entity
    attribute_is_modified: bool = False

@dataclass
class CurriedObject:
    function_instance: EisenInstance = None
    entity: Entity = None
    curried_params: list[CurriedObject] = None
