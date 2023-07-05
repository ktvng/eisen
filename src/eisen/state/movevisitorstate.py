from __future__ import annotations

import uuid
from alpaca.clr import AST
from alpaca.concepts import Context, Module
from alpaca.concepts import AbstractException

from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor
from eisen.moves.moveepoch import Entity, Lifetime, Dependency, CurriedObject

class MoveVisitorState(State_PostInstanceVisitor):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    # note: updated_epoch_uids are outside the context but updated inside it
    def but_with(self,
            ast: AST = None,
            context: Context = None,
            mod: Module = None,
            updated_epoch_uids: set[uuid.UUID] = None,
            nest_depth: int = None,
            place: str = None,
            exceptions: list[AbstractException] = None,
            curried_objects: dict[uuid.UUID, CurriedObject] = None
            ) -> MoveVisitorState:

        return self._but_with(
            ast=ast,
            context=context,
            mod=mod,
            updated_epoch_uids=updated_epoch_uids,
            nest_depth=nest_depth,
            place=place,
            curried_objects=curried_objects,
            exceptions=exceptions)

    @staticmethod
    def create_from_basestate(state: State_PostInstanceVisitor) -> MoveVisitorState:
        """
        Create a new instance of NilCheckState from any descendant of BaseState

        :param state: The BaseState instance
        :type state: BaseState
        :return: A instance of NilCheckState
        :rtype: NilCheckState
        """
        return MoveVisitorState(**state._get(), updated_epoch_uids=set(), nest_depth=0,
                                place="", curried_objects={})

    def get_entity_by_uid(self, uid: uuid.UUID) -> Entity:
        if uid == uuid.UUID(int=0):
            return Entity.create_anonymous()
        return self.get_context().get_entity(uid)

    def get_entity_by_name(self, name: str) -> Entity:
        uid = self.get_entity_uid(name)
        return self.get_entity_by_uid(uid)

    def add_entity(self, epoch: Entity)-> Entity:
        self.get_context().add_entity(epoch.uid, epoch)

    def add_entity_uid(self, name: str, uid: uuid.UUID):
        self.get_context().add_entity_uuid(name, uid)

    def get_entity_uid(self, name: str) -> uuid.UUID:
        return self.get_context().get_entity_uuid(name)

    def add_new_entity(self, name: str, is_let: bool = False, depth: int = 0) -> Entity:
        lifetime: Lifetime = None
        match self.place:
            case "args": lifetime = Lifetime.arg()
            case "rets": lifetime = Lifetime.ret()
            case "": lifetime = Lifetime.local(depth)

        uid = uuid.uuid4()
        new_epoch = Entity(
            dependencies=set(),
            lifetime=lifetime,
            generation=0,
            name=name,
            uid=uid,
            is_let=is_let)
        # print("!!", new_epoch)
        self.add_entity(new_epoch)
        self.add_entity_uid(name, uid)
        return new_epoch

    def merge_epochs(self, epochs: list[Entity]) -> Entity:
        dependencies = set([Dependency(e.uid, e.generation) for e in epochs])
        return Entity(
            dependencies=dependencies,
            lifetime=Lifetime.transient(),
            generation=0,
            name="",
            uid=uuid.UUID(int=0))

    def get_updated_epoch_uids(self) -> set[uuid.UUID]:
        return self.updated_epoch_uids

    def get_nest_depth(self) -> int:
        return self.nest_depth

    def restore_to_healthy(self, entity: Entity):
        entity.dependencies = set(dep for dep in entity.dependencies
            if not entity.lifetime.longer_than(self.get_entity_by_uid(dep.uid).lifetime))

    def get_curried_object(self, uid: uuid.UUID) -> CurriedObject:
        return self.curried_objects.get(uid, None)

    def add_curried_object(self, uid: uuid.UUID, obj: CurriedObject):
        self.curried_objects[uid] = obj
