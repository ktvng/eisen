from __future__ import annotations

import uuid
from dataclasses import dataclass
from alpaca.utils import Visitor
from alpaca.clr import CLRList
from alpaca.concepts import Type, Context, Module

import eisen.adapters as adapters
from eisen.common import no_assign_binary_ops, boolean_return_ops
from eisen.state.movevisitorstate import MoveVisitorState
from eisen.validation.validate import Validate
from eisen.moves.moveepoch import LvalIdentity, MoveEpoch, Dependency

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

    @staticmethod
    def update_move_epoch(state: State, lval: LvalIdentity, rval: MoveEpoch):
        new_epoch = MoveEpoch(
            dependencies=lval.move_epoch.dependencies.copy(),
            lifetime=lval.move_epoch.lifetime,
            generation=lval.move_epoch.generation,
            name=lval.move_epoch.name,
            uid=lval.move_epoch.uid,
            is_let=lval.move_epoch.is_let)

        match (lval.attribute_is_modified, rval.is_let):
            case True, True:
                new_epoch.dependencies.add(
                    Dependency(uid=rval.uid, generation=rval.generation))
            case True, False:
                for dep in rval.dependencies: new_epoch.dependencies.add(dep)
            case False, True:
                new_epoch.dependencies = set([Dependency(uid=rval.uid, generation=rval.generation)])
            case False, False:
                new_epoch.dependencies = rval.dependencies.copy()

        if Validate.epoch_dependencies_are_ok(state, new_epoch).failed():
            state.restore_to_healthy(new_epoch)

        state.add_move_epoch(new_epoch)
        if lval.move_epoch.lifetime.depth < state.get_nest_depth():
            state.updated_epoch_uids.add(lval.move_epoch.uid)

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
        # print(adapters.CommonFunction(state).get_name())
        fn_context = state.create_block_context()
        fn_context.add_move_epoch(uuid.UUID(int=0), MoveEpoch.create_anonymous())
        for child in state.get_child_asls():
            fn.apply(state.but_with(
                asl=child,
                context=fn_context))

    @Visitor.for_asls(*adapters.ArgsRets.asl_types)
    def _argsrets(fn, state: State):
        if not state.get_asl().has_no_children():
            fn.apply(state.but_with(
                asl=state.first_child(),
                place=adapters.ArgsRets(state).get_node_type()))

    @Visitor.for_asls("=")
    def _eq(fn, state: State):
        lvals = LvalMoveVisitor().apply(state.but_with_first_child())
        rights = fn.apply(state.but_with_second_child())
        for lval, rval in zip(lvals, rights):
            # print(lval.move_epoch.name, rval.name, lval.move_epoch.lifetime.is_ret(), rval.lifetime.is_local(), rval)
            MoveVisitor.update_move_epoch(state, lval, rval)

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

        if node.is_pure_function_call():
            # print("name", node.get_function_instance())
            F_deps = state.get_deps_of_function(node.get_function_instance())
            param_epochs = fn.apply(state.but_with(asl=node.get_params_asl()))
            for type_, epoch in zip(node.get_function_argument_type().unpack_into_parts(), param_epochs):
                if type_.restriction.is_move():
                    epoch.mark_as_gone()

            updated_param_epochs = []
            for param_epoch, additional_epochs in zip(param_epochs, F_deps.apply_to_parameters_for_arguments(param_epochs)):
                updated_param_epochs.append(param_epoch.add_dependencies_on(additional_epochs))
                if Validate.epoch_dependencies_are_ok(state, updated_param_epochs[-1]).failed():
                    state.restore_to_healthy(updated_param_epochs[-1])

            return [state.merge_epochs(e) for e in F_deps.apply_to_parameters_for_return_values(updated_param_epochs)]
        else:
            param_epochs = fn.apply(state.but_with(asl=node.get_params_asl()))
            return [MoveEpoch.create_anonymous()] * len(param_epochs)

    @Visitor.for_asls("curry_call")
    def _curry_call(fn, state: State):
        # create a new epoch as this will return a new "entity"
        epoch = MoveEpoch.create_anonymous()
        lval = LvalIdentity(move_epoch=epoch)
        # this new epoch should have the same dependencies as function being curried
        MoveVisitor.update_move_epoch(state, lval, fn.apply(state.but_with_first_child())[0])

        # this new epoch should also have dependencies on each child parameter.
        lval.attribute_is_modified = True
        for rval in fn.apply(state.but_with_second_child()):
            MoveVisitor.update_move_epoch(state, lval, rval)
        return [MoveEpoch.create_anonymous()]

    @Visitor.for_asls(*adapters.InferenceAssign.asl_types)
    def _idecls(fn, state: State):
        node = adapters.InferenceAssign(state)
        lvals = []
        for name in node.get_names():
            lvals.append(LvalIdentity(state.add_new_move_epoch(
                name=name,
                depth=state.get_nest_depth(),
                is_let=node.get_is_let())))
        rvals = fn.apply(state.but_with_second_child())
        for lval, rval in zip(lvals, rvals):
            MoveVisitor.update_move_epoch(state, lval, rval)

    @Visitor.for_asls(*adapters.Typing.asl_types)
    def _decls(fn, state: State):
        node = adapters.Typing(state)
        for name in node.get_names():
            state.add_new_move_epoch(
                name=name,
                depth=state.get_nest_depth(),
                is_let=node.get_is_let())

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
        fn.apply(state.but_with(
            asl=state.first_child(),
            context=state.create_block_context(),
            nest_depth=state.get_nest_depth() + 1))

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
                updated_epoch_uids=updated_epoch_uids,
                nest_depth=state.get_nest_depth() + 1))

        MoveVisitor._update_epochs_after_conditional(state, if_contexts, updated_epoch_uids)

    @staticmethod
    def _update_epochs_after_conditional(state: State, if_contexts: list[Context], updated_epoch_uids: set[uuid.UUID]):
        for uid in updated_epoch_uids:
            branch_epochs = [state.but_with(context=branch_context).get_move_epoch_by_uid(uid)
                for branch_context in if_contexts]
            branch_epochs = [e for e in branch_epochs if e is not None]
            new_epoch_for_uid = state.get_move_epoch_by_uid(uid).merge_dependencies_of(branch_epochs)

            if Validate.epoch_dependencies_are_ok(state, new_epoch_for_uid).failed():
                state.restore_to_healthy(new_epoch_for_uid)

            state.add_move_epoch(new_epoch_for_uid)


    @Visitor.for_asls("mod")
    def _mod(fn, state: State):
        adapters.Mod(state).enter_module_and_apply(fn)

    @Visitor.for_tokens
    def _tokens(fn, state: State):
        return [MoveEpoch.create_anonymous()]
