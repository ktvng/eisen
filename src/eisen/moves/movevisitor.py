from __future__ import annotations

import uuid
from dataclasses import dataclass
from alpaca.utils import Visitor
from alpaca.clr import CLRList
from alpaca.concepts import Type, Context, Module

import eisen.adapters as adapters
from eisen.common import no_assign_binary_ops, boolean_return_ops
from eisen.state.state_postspreadvisitor import State_PostSpreadVisitor
from eisen.validation.validate import Validate

class MoveVisitorState(State_PostSpreadVisitor):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    def but_with(self,
            asl: CLRList = None,
            context: Context = None,
            mod: Module = None,
            updated_epoch_uids: set[uuid.UUID] = None,
            ) -> MoveVisitorState:

        return self._but_with(
            asl=asl,
            context=context,
            mod=mod,
            updated_epoch_uids=updated_epoch_uids)

    @staticmethod
    def create_from_basestate(state: State_PostSpreadVisitor) -> MoveVisitorState:
        """
        Create a new instance of NilCheckState from any descendant of BaseState

        :param state: The BaseState instance
        :type state: BaseState
        :return: A instance of NilCheckState
        :rtype: NilCheckState
        """
        return MoveVisitorState(**state._get(), updated_epoch_uids=set())

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

    def add_new_move_epoch(self, name: str, is_let: bool = False) -> MoveEpoch:
        uid = uuid.uuid4()
        new_epoch = MoveEpoch(
            dependencies=[],
            generation=0,
            name=name,
            uid=uid,
            is_let=is_let)
        self.add_move_epoch(new_epoch)
        self.add_entity_uid(name, uid)
        return new_epoch

    def update_move_epoch(self, lval: LvalIdentity, rval: MoveEpoch):
        new_epoch = MoveEpoch(
            dependencies=lval.move_epoch.dependencies.copy(),
            generation=lval.move_epoch.generation,
            name=lval.move_epoch.name,
            uid=lval.move_epoch.uid,
            is_let=lval.move_epoch.is_let)

        match (lval.attribute_is_modified, rval.is_let):
            case True, True:
                new_epoch.dependencies.append(
                    Dependency(uid=rval.uid, generation=rval.generation))
            case True, False:
                new_epoch.dependencies.extend(rval.dependencies)
            case False, True:
                new_epoch.dependencies = [Dependency(uid=rval.uid, generation=rval.generation)]
            case False, False:
                new_epoch.dependencies = rval.dependencies.copy()

        self.add_move_epoch(new_epoch)
        self.updated_epoch_uids.add(lval.move_epoch.uid)

    def get_updated_epoch_uids(self) -> set[uuid.UUID]:
        return self.updated_epoch_uids

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

    def merge_dependencies(self, other: list[MoveEpoch]) -> MoveEpoch:
        new_epoch = MoveEpoch(
            dependencies=self.dependencies,
            generation=self.generation,
            name=self.name,
            uid=self.uid,
            is_let=self.is_let,
            moved_away=self.moved_away)
        for o in other:
            new_epoch.dependencies += o.dependencies
        return new_epoch

@dataclass
class Dependency:
    uid: uuid.UUID
    generation: int

@dataclass
class LvalIdentity:
    move_epoch: MoveEpoch
    attribute_is_modified: bool = False


State = MoveVisitorState

class LvalMoveVisitor(Visitor):
    def apply(self, state: State) -> list[LvalIdentity]:
        return self._route(state.get_asl(), state)

    @Visitor.for_asls("ref")
    def _ref(fn, state: State):
        return [LvalIdentity(
            move_epoch=state.get_move_epoch_by_name(adapters.Ref(state).get_name()),
            attribute_is_modified=False)]

    @Visitor.for_asls(".")
    def _dot(fn, state: State):
        return [LvalIdentity(
            move_epoch=state.get_move_epoch_by_name(adapters.Scope(state).get_object_name()),
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
        self.apply(MoveVisitorState.create_from_basestate(state))
        return state


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
            state.update_move_epoch(lval, rval)

    @Visitor.for_asls("+=", "*=", "/=", "-=")
    def _math_eq(fn, state: State):
        fn.apply(state.but_with_first_child())
        fn.apply(state.but_with_second_child())

    @Visitor.for_asls("ref")
    def _ref(fn, state: State):
        epoch = state.get_move_epoch_by_name(adapters.Ref(state).get_name())
        Validate.healthy_dependencies(state, epoch)
        return [epoch]

    @Visitor.for_asls(".")
    def _dot(fn, state: State):
        epoch = state.get_move_epoch_by_name(adapters.Scope(state).get_object_name())
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
        if node.is_print():
            fn.apply(state.but_with(asl=node.get_params_asl()))
            return []

        F_deps = state.get_deps_of_function(node.get_function_instance())
        print(node.get_function_instance(), F_deps)
        epochs = fn.apply(state.but_with(asl=node.get_params_asl()))
        for type_, epoch in zip(node.get_function_argument_type().unpack_into_parts(), epochs):
            if type_.restriction.is_move():
                epoch.mark_as_gone()

        n = len(node.get_params_asl()._list)
        return [MoveEpoch.create_anonymous()] * n

    @Visitor.for_asls("curry_call")
    def _curry_call(fn, state: State):
        # create a new epoch as this will return a new "entity"
        epoch = MoveEpoch.create_anonymous()
        lval = LvalIdentity(move_epoch=epoch)
        # this new epoch should have the same dependencies as function being curried
        state.update_move_epoch(lval, fn.apply(state.but_with_first_child())[0])

        # this new epoch should also have dependencies on each child parameter.
        lval.attribute_is_modified = True
        for rval in fn.apply(state.but_with_second_child()):
            state.update_move_epoch(lval, rval)
        return [MoveEpoch.create_anonymous()]

    @Visitor.for_asls(*adapters.InferenceAssign.asl_types)
    def _idecls(fn, state: State):
        node = adapters.InferenceAssign(state)
        lvals = []
        for name in node.get_names():
            lvals.append(LvalIdentity(state.add_new_move_epoch(name, node.get_is_let())))
        rvals = fn.apply(state.but_with_second_child())
        for lval, rval in zip(lvals, rvals):
            state.update_move_epoch(lval, rval)

    @Visitor.for_asls(*adapters.Typing.asl_types)
    def _decls(fn, state: State):
        node = adapters.Typing(state)
        for name in node.get_names():
            state.add_new_move_epoch(name, node.get_is_let())

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
        updated_epoch_uids: set[uuid.UUID] = set()
        if_contexts: list[Context] = []
        for child in state.get_child_asls():
            context = state.create_block_context()
            if_contexts.append(context)
            fn.apply(state.but_with(
                asl=child,
                context=context,
                updated_epoch_uids=updated_epoch_uids))

        MoveVisitor._update_epochs_after_conditional(state, if_contexts, updated_epoch_uids)

    @staticmethod
    def _update_epochs_after_conditional(state: State, if_contexts: list[Context], updated_epoch_uids: set[uuid.UUID]):
        for uid in updated_epoch_uids:
            branch_epochs = [state.but_with(context=branch_context).get_move_epoch_by_uid(uid)
                for branch_context in if_contexts]
            branch_epochs = [e for e in branch_epochs if e is not None]
            new_epoch_for_uid = state.get_move_epoch_by_uid(uid).merge_dependencies(branch_epochs)
            state.add_move_epoch(new_epoch_for_uid)

    @Visitor.for_asls("mod")
    def _mod(fn, state: State):
        adapters.Mod(state).enter_module_and_apply(fn)

    @Visitor.for_tokens
    def _tokens(fn, state: State):
        return [MoveEpoch.create_anonymous()]
