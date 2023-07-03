from __future__ import annotations

import uuid
from dataclasses import dataclass
from alpaca.utils import Visitor
from alpaca.concepts import Type, Context, Module

import eisen.adapters as adapters
from eisen.common import no_assign_binary_ops, boolean_return_ops
from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor
from eisen.validation.validate import Validate

State = State_PostInstanceVisitor

@dataclass
class MoveEpoch:
    dependencies: list[Dependency]
    generation: int = 0
    name: str = None
    uid: uuid.UUID = uuid.UUID(int=0)
    is_let: bool = False
    moved_away: bool = False

    @staticmethod
    def create_anonymous():
        return MoveEpoch(dependencies=[], uid=uuid.UUID(int=0))

    def increment_generation(self):
        self.generation += 1

    def mark_as_gone(self):
        self.moved_away = True

@dataclass
class Dependency:
    uid: uuid.UUID
    generation: int

@dataclass
class LvalIdentity:
    move_epoch: MoveEpoch
    attribute_is_modified: bool = False

class LvalMoveVisitor(Visitor):
    def apply(self, state: State) -> list[LvalIdentity]:
        return self._route(state.get_asl(), state)

    @Visitor.for_asls("ref")
    def _ref(fn, state: State):
        return [LvalIdentity(
            move_epoch=MoveVisitor.get_move_epoch_by_name(state, adapters.Ref(state).get_name()),
            attribute_is_modified=False)]

    @Visitor.for_asls(".")
    def _dot(fn, state: State):
        return [LvalIdentity(
            move_epoch=MoveVisitor.get_move_epoch_by_name(state, adapters.Scope(state).get_object_name()),
            attribute_is_modified=True)]

    @Visitor.for_asls("lvals")
    def _lvals(fn, state: State):
        lvals = []
        for child in state.get_all_children():
            lvals += fn.apply(state.but_with(asl=child))
        return lvals


class MoveVisitor(Visitor):
    def apply(self, state: State) -> list[MoveEpoch]:
        return self._route(state.get_asl(), state)

    def run(self, state: State) -> State:
        self.apply(state)
        return state

    @staticmethod
    def get_move_epoch_by_uid(state: State, uid: uuid.UUID) -> MoveEpoch:
        if uid == uuid.UUID(int=0):
            return MoveEpoch.create_anonymous()
        return state.get_context().get_move_epoch(uid)


    @staticmethod
    def get_move_epoch_by_name(state: State, name: str) -> MoveEpoch:
        uid = MoveVisitor.get_entity_uid(state, name)
        return MoveVisitor.get_move_epoch_by_uid(state, uid)

    @staticmethod
    def add_move_epoch(state: State, epoch: MoveEpoch)-> MoveEpoch:
        state.get_context().add_move_epoch(epoch.uid, epoch)

    @staticmethod
    def add_entity_uid(state: State, name: str, uid: uuid.UUID):
        state.get_context().add_entity_uuid(name, uid)

    @staticmethod
    def get_entity_uid(state: State, name: str) -> uuid.UUID:
        return state.get_context().get_entity_uuid(name)

    @staticmethod
    def add_new_move_epoch(state: State, name: str, is_let: bool = False) -> MoveEpoch:
        uid = uuid.uuid4()
        new_epoch = MoveEpoch(
            dependencies=[],
            generation=0,
            name=name,
            uid=uid,
            is_let=is_let)
        MoveVisitor.add_move_epoch(state, new_epoch)
        MoveVisitor.add_entity_uid(state, name, uid)
        return new_epoch

    @staticmethod
    def update_move_epoch(lval: LvalIdentity, rval: MoveEpoch):
        match (lval.attribute_is_modified, rval.is_let):
            case True, True:
                lval.move_epoch.dependencies.append(
                    Dependency(uid=rval.uid, generation=rval.generation))
            case True, False:
                lval.move_epoch.dependencies.extend(rval.dependencies)
            case False, True:
                lval.move_epoch.dependencies = [Dependency(uid=rval.uid, generation=rval.generation)]
            case False, False:
                lval.move_epoch.dependencies = rval.dependencies.copy()

    # TODO: cond and if need to be handled properly
    @Visitor.for_asls("start", "seq", "cond", "prod_type")
    def _start(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_asls("fn", "new_vec")
    def _anonymous(fn, state: State):
        return [MoveEpoch.create_anonymous()]

    # TODO: do this
    @Visitor.for_asls("index")
    def _index(fn, state: State):
        return [MoveEpoch.create_anonymous()]

    @Visitor.for_asls("variant", "is_call", "interface", "return")
    def _nothing(fn, state: State):
        return

    @Visitor.for_asls("struct")
    def _struct(fn, state: State):
        if adapters.Struct(state).has_create_asl():
            fn.apply(state.but_with(asl=adapters.Struct(state).get_create_asl()))

    @Visitor.for_asls("create", "def")
    def _create(fn, state: State):
        fn_context = state.create_block_context()
        fn_context.add_move_epoch(uuid.UUID(int=0), MoveEpoch.create_anonymous())
        for child in state.get_child_asls():
            fn.apply(state.but_with(
                asl=child,
                context=fn_context))

    @Visitor.for_asls(*adapters.ArgsRets.asl_types)
    def _argsrets(fn, state: State):
        if not state.get_asl().has_no_children():
            fn.apply(state.but_with_first_child())

    @Visitor.for_asls("=")
    def _eq(fn, state: State):
        lvals = LvalMoveVisitor().apply(state.but_with_first_child())
        rights = fn.apply(state.but_with_second_child())
        for lval, rval in zip(lvals, rights):
            MoveVisitor.update_move_epoch(lval, rval)

    @Visitor.for_asls("+=", "*=", "/=", "-=")
    def _math_eq(fn, state: State):
        fn.apply(state.but_with_first_child())
        fn.apply(state.but_with_second_child())

    @Visitor.for_asls("ref")
    def _ref(fn, state: State):
        uid = MoveVisitor.get_entity_uid(state, adapters.Ref(state).get_name())
        epoch = MoveVisitor.get_move_epoch_by_uid(state, uid)
        Validate.healthy_dependencies(state, epoch)
        return [epoch]

    @Visitor.for_asls(".")
    def _dot(fn, state: State):
        uid = MoveVisitor.get_entity_uid(state, adapters.Scope(state).get_object_name())
        epoch = MoveVisitor.get_move_epoch_by_uid(state, uid)
        Validate.healthy_dependencies(state, epoch)
        return [epoch]

    @Visitor.for_asls("cast")
    def _cast(fn, state: State):
        return fn.apply(state.but_with_first_child())

    # TODO: write this
    # Note: should we allow references to the moved object here? Might be
    # necessary if we want to move a pair of objects that refer to each other.
    @Visitor.for_asls("call")
    def _call(fn, state: State):
        node = adapters.Call(state)
        epochs = fn.apply(state.but_with(asl=node.get_params_asl()))
        for type_, epoch in zip(node.get_function_argument_type().unpack_into_parts(), epochs):
            if type_.restriction.is_move():
                epoch.mark_as_gone()

        n = len(node.get_params_asl()._list)
        return [MoveEpoch.create_anonymous()] * n

    # TODO: fix this
    @Visitor.for_asls("curry_call")
    def _curry_call(fn, state: State):
        return [MoveEpoch.create_anonymous()]

    @Visitor.for_asls(*adapters.InferenceAssign.asl_types)
    def _idecls(fn, state: State):
        node = adapters.InferenceAssign(state)
        lvals = []
        for name in node.get_names():
            lvals.append(LvalIdentity(MoveVisitor.add_new_move_epoch(state, name, node.get_is_let())))
        rvals = fn.apply(state.but_with_second_child())
        for lval, rval in zip(lvals, rvals):
            MoveVisitor.update_move_epoch(lval, rval)

    @Visitor.for_asls(*adapters.Typing.asl_types)
    def _decls(fn, state: State):
        node = adapters.Typing(state)
        for name in node.get_names():
            MoveVisitor.add_new_move_epoch(state, name, node.get_is_let())

    @Visitor.for_asls(*no_assign_binary_ops, *boolean_return_ops)
    def _binop(fn, state: State):
        fn.apply(state.but_with_first_child())
        fn.apply(state.but_with_second_child())
        return [MoveEpoch.create_anonymous()]

    @Visitor.for_asls("!")
    def _not(fn, state: State):
        fn.apply(state.but_with_first_child())
        return [MoveEpoch.create_anonymous()]

    @Visitor.for_asls("params", "tuple", "curried")
    def _params(fn, state: State):
        epochs = []
        for child in state.get_all_children():
            epochs += fn.apply(state.but_with(asl=child))
        return epochs

    @Visitor.for_asls("while")
    def _while(fn, state: State):
        adapters.While(state).enter_context_and_apply(fn)

    @Visitor.for_asls("if")
    def _if(fn, state: State) -> Type:
        adapters.If(state).enter_context_and_apply(fn)

    @Visitor.for_asls("mod")
    def _mod(fn, state: State):
        adapters.Mod(state).enter_module_and_apply(fn)

    @Visitor.for_tokens
    def _tokens(fn, state: State):
        return [MoveEpoch.create_anonymous()]
