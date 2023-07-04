from __future__ import annotations

import uuid
from alpaca.clr import CLRList
from alpaca.concepts import Type, Context, Module

from eisen.state.state_postspreadvisitor import State_PostSpreadVisitor
from eisen.moves.moveepoch import MoveEpoch, Lifetime, Dependency, LvalIdentity

class MoveVisitorState(State_PostSpreadVisitor):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    def but_with(self,
            asl: CLRList = None,
            context: Context = None,
            mod: Module = None,
            updated_epoch_uids: set[uuid.UUID] = None,
            nest_depth: int = None,
            place: str = None
            ) -> MoveVisitorState:

        return self._but_with(
            asl=asl,
            context=context,
            mod=mod,
            updated_epoch_uids=updated_epoch_uids,
            nest_depth=nest_depth,
            place=place)

    @staticmethod
    def create_from_basestate(state: State_PostSpreadVisitor) -> MoveVisitorState:
        """
        Create a new instance of NilCheckState from any descendant of BaseState

        :param state: The BaseState instance
        :type state: BaseState
        :return: A instance of NilCheckState
        :rtype: NilCheckState
        """
        return MoveVisitorState(**state._get(), updated_epoch_uids=set(), nest_depth=0,
                                place="")

    def get_move_epoch_by_uid(self, uid: uuid.UUID) -> MoveEpoch:
        if uid == uuid.UUID(int=0):
            return MoveEpoch.create_anonymous()
        return self.get_context().get_move_epoch(uid)

    def get_move_epoch_by_name(self, name: str) -> MoveEpoch:
        uid = self.get_entity_uid(name)
        return self.get_move_epoch_by_uid(uid)

    def add_move_epoch(self, epoch: MoveEpoch)-> MoveEpoch:
        self.get_context().add_move_epoch(epoch.uid, epoch)

    def add_entity_uid(self, name: str, uid: uuid.UUID):
        self.get_context().add_entity_uuid(name, uid)

    def get_entity_uid(self, name: str) -> uuid.UUID:
        return self.get_context().get_entity_uuid(name)

    def add_new_move_epoch(self, name: str, is_let: bool = False, depth: int = 0) -> MoveEpoch:
        lifetime: Lifetime = None
        match self.place:
            case "args": lifetime = Lifetime.arg()
            case "rets": lifetime = Lifetime.ret()
            case "": lifetime = Lifetime.local(depth)

        uid = uuid.uuid4()
        new_epoch = MoveEpoch(
            dependencies=set(),
            lifetime=lifetime,
            generation=0,
            name=name,
            uid=uid,
            is_let=is_let)
        # print("!!", new_epoch)
        self.add_move_epoch(new_epoch)
        self.add_entity_uid(name, uid)
        return new_epoch

    def merge_epochs(self, epochs: list[MoveEpoch]) -> MoveEpoch:
        dependencies = set([Dependency(e.uid, e.generation) for e in epochs])
        return MoveEpoch(
            dependencies=dependencies,
            lifetime=Lifetime.transient(),
            generation=0,
            name="",
            uid=uuid.UUID(int=0))

    def get_updated_epoch_uids(self) -> set[uuid.UUID]:
        return self.updated_epoch_uids

    def get_nest_depth(self) -> int:
        return self.nest_depth

    def restore_to_healthy(self, move_epoch: MoveEpoch):
        move_epoch.dependencies = set(dep for dep in move_epoch.dependencies
            if not move_epoch.lifetime.longer_than(self.get_move_epoch_by_uid(dep.uid).lifetime))
