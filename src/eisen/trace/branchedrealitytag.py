from __future__ import annotations
from dataclasses import dataclass
import uuid

@dataclass
class BranchedRealityTag:
    uid: uuid.UUID
    branch_number: int
    parent: BranchedRealityTag = None

    def __hash__(self) -> int:
        return hash(hash(self.uid) + hash(self.branch_number))

    def symbiotic_with(self, tag: BranchedRealityTag) -> bool:
        return tag is None or self == tag or (
            self.parent and self.parent.symbiotic_with(tag))

    def symbiotic_with_any(self, tags: set[BranchedRealityTag]) -> bool:
        return any(self.symbiotic_with(tag) for tag in tags)

    def is_from_base_branch(self) -> bool:
        return self == BranchedRealityTag(uuid.UUID(int=0), 0)

    def __str__(self) -> str:
        return f"{str(self.uid)[0:5]}.{self.branch_number}"
