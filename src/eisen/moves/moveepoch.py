from __future__ import annotations

import uuid
from dataclasses import dataclass

@dataclass
class MoveEpoch:
    dependencies: set[Dependency]
    lifetime: Lifetime
    generation: int = 0
    name: str = None
    uid: uuid.UUID = uuid.UUID(int=0)
    is_let: bool = False
    moved_away: bool = False

    @staticmethod
    def create_anonymous():
        return MoveEpoch(dependencies=set(), lifetime=Lifetime.primitive(), uid=uuid.UUID(int=0))

    def increment_generation(self):
        self.generation += 1

    def mark_as_gone(self):
        self.moved_away = True

    def add_dependencies_on(self, others: list[MoveEpoch]) -> MoveEpoch:
        new_epoch = MoveEpoch(
            dependencies=self.dependencies,
            lifetime=self.lifetime,
            generation=self.generation,
            name=self.name,
            uid=self.uid,
            is_let=self.is_let,
            moved_away=self.moved_away)
        for o in others:
            new_epoch.dependencies.add(Dependency(o.uid, o.generation))
        return new_epoch

    def merge_dependencies_of(self, others: list[MoveEpoch]) -> MoveEpoch:
        new_epoch = MoveEpoch(
            dependencies=self.dependencies,
            lifetime=self.lifetime,
            generation=self.generation,
            name=self.name,
            uid=self.uid,
            is_let=self.is_let,
            moved_away=self.moved_away)
        for o in others:
            for d in o.dependencies:
                new_epoch.dependencies.add(d)
        return new_epoch

varieties = ["arg", "ret", "local", "primitive", "transient"]
@dataclass
class Lifetime:
    variety: str
    depth: int = 0

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
    move_epoch: MoveEpoch
    attribute_is_modified: bool = False
