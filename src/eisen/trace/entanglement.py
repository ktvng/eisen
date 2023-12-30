from __future__ import annotations
import uuid

class Entanglement:
    def __init__(self, uid: uuid.uuid4 | None = None, sub_entanglements: set[uuid.UUID] = None) -> None:
        self.uid = uuid.uuid4() if uid is None else uid
        self.sub_entanglements: set[uuid.UUID] = set() if sub_entanglements is None else sub_entanglements

    def __eq__(self, __value: object) -> bool:
        if __value is None: return False
        return (self.uid == __value.uid
            and len(self.sub_entanglements) == len(__value.sub_entanglements)
            and all(x == y for x, y in zip(self.sub_entanglements, __value.sub_entanglements)))

    def __str__(self) -> str:
        parents = [str(uid)[0:5] for uid in self.sub_entanglements]
        return str(self.uid)[0:5] + ("." + ".".join(parents) if parents else "")

    def add_sub_entanglement(self, uid: uuid.UUID) -> None:
        self.sub_entanglements.add(uid)

    def with_sub_entanglement(self, uid: uuid.UUID) -> Entanglement:
        sub_entanglements = self.sub_entanglements.copy()
        sub_entanglements.add(uid)
        return Entanglement(self.uid, sub_entanglements)

    def matches(self, other: Entanglement) -> bool:
        if other is None: return True
        if self.uid == other.uid: return True
        return other.uid in self.sub_entanglements or self.uid in other.sub_entanglements
