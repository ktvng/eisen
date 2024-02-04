from __future__ import annotations
import uuid
from dataclasses import dataclass, field

@dataclass
class Entanglement:
    """
    An entanglement represents an interaction between two different entities which may arise due to
    their concurrent modification inside the branch of a conditional statement. For example:

        fn example(b: obj(), mut B: ptr) {
            let a = obj()
            let A = ptr()
            let var p: obj
            let var P: ptr

            if (...) {
                p = a
                P = A
            }
            else {
                p = b
                P = B
            }

            P.obj = p
        }

    In the above code example, due to the nature of the conditional branching, we have the following
    entanglements, (1) A ~ a and (2) B ~ b as these are concurrent modifications within the
    conditional branch.

    Preserving and respecting these entanglements is important because on the last line, the human
    reader can observe that there is no immediate memory issue, as the assignment could either
    assign A.obj = a or B.obj = b. This is exactly what is meant by the entanglements A ~ a and
    B ~ b.

    Thus, while p may depend on either a or b, and P may depend on either A or B, in reality, these
    are parallel dependencies, and the entanglement ensures that we never cross A.obj = b, or vice
    versa.
    """

    uid: uuid.UUID | None
    sub_entanglements: set[uuid.UUID] = field(default_factory=set)

    def __str__(self) -> str:
        parents = [str(uid)[0:5] for uid in self.sub_entanglements]
        return str(self.uid)[0:5] + ("." + ".".join(parents) if parents else "")

    def with_sub_entanglement(self, uid: uuid.UUID) -> Entanglement:
        """
        Create a new Entanglement with the [uid] added as a sub entanglement
        """
        sub_entanglements = self.sub_entanglements.copy()
        sub_entanglements.add(uid)
        return Entanglement(self.uid, sub_entanglements)

    def matches(self, other: Entanglement) -> bool:
        """
        True if the [other] entanglement matches this entanglement, e.g. they are of the same
        entanglement.
        """
        return (other is None   # no entanglement, always matches
            or self.uid == other.uid    # identical entanglements match
            or other.uid in self.sub_entanglements)     # other is taken from a parent if-context
