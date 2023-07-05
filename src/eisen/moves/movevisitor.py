from __future__ import annotations

import uuid
from alpaca.utils import Visitor
from alpaca.concepts import Type, Context

import eisen.adapters as adapters
from eisen.common import no_assign_binary_ops, boolean_return_ops
from eisen.common.eiseninstance import EisenInstance
from eisen.state.movevisitorstate import MoveVisitorState
from eisen.validation.validate import Validate
from eisen.moves.moveepoch import LvalIdentity, Entity, Dependency

State = MoveVisitorState

class LvalMoveVisitor(Visitor):
    def apply(self, state: State) -> list[LvalIdentity]:
        return self._route(state.get_ast(), state)

    @Visitor.for_ast_types("ref")
    def _ref(fn, state: State):
        return [LvalIdentity(
            entity=state.get_entity_by_name(adapters.Ref(state).get_name()),
            attribute_is_modified=False)]

    @Visitor.for_ast_types(".")
    def _dot(fn, state: State):
        return [LvalIdentity(
            entity=state.get_entity_by_name(adapters.Scope(state).get_object_name()),
            attribute_is_modified=True)]

    @Visitor.for_ast_types("lvals")
    def _lvals(fn, state: State):
        lvals = []
        for child in state.get_all_children():
            lvals += fn.apply(state.but_with(ast=child))
        return lvals


class MoveVisitor(Visitor):
    def __init__(self, debug: bool = False):
        super().__init__(False)
        self.deps_db = FunctionDepsDatabase2()

    def apply(self, state: State) -> list[Entity]:
        return self._route(state.get_ast(), state)

    def run(self, state: State) -> State:
        self.apply(MoveVisitorState.create_from_basestate(state))
        return state

    @staticmethod
    def add_epoch_uid_as_updated(state: State, lval: Entity, rval: Entity):
        if lval.lifetime.depth < state.get_nest_depth() and lval != rval:
            state.get_updated_epoch_uids().add(lval.uid)
        state.add_entity(rval)

    @staticmethod
    def update_entity(state: State, lval: LvalIdentity, rval: Entity):
        new_epoch = Entity(
            dependencies=lval.entity.dependencies.copy(),
            lifetime=lval.entity.lifetime,
            generation=lval.entity.generation,
            name=lval.entity.name,
            uid=lval.entity.uid,
            is_let=lval.entity.is_let)

        # if rval.is_let or rval.lifetime.is_arg, then the lval must depend on the actual identity
        # of the rval, not any of its dependencies.
        match (lval.attribute_is_modified, rval.is_let | rval.lifetime.is_arg()):
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

        MoveVisitor.add_epoch_uid_as_updated(state, lval.entity, new_epoch)

    # TODO: cond and if need to be handled properly
    @Visitor.for_ast_types("start", "seq", "cond", "prod_type")
    def _start(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_ast_types("fn", "new_vec")
    def _anonymous(fn, state: State):
        return [Entity.create_anonymous()]

    # TODO: do this
    @Visitor.for_ast_types("index")
    def _index(fn, state: State):
        return [Entity.create_anonymous()]

    @Visitor.for_ast_types("variant", "is_call", "interface", "return")
    def _nothing(fn, state: State):
        return

    @Visitor.for_ast_types("struct")
    def _struct(fn, state: State):
        if adapters.Struct(state).has_create_ast():
            fn.apply(state.but_with(ast=adapters.Struct(state).get_create_ast()))

    @Visitor.for_ast_types("create", "def")
    def _create(fn, state: State):
        found_deps = fn.deps_db.lookup_deps_of(adapters.Def(state).get_function_instance())
        if found_deps:
            return found_deps

        # print(adapters.CommonFunction(state).get_name())
        fn_context = state.create_isolated_context()
        fn_context.add_entity(uuid.UUID(int=0), Entity.create_anonymous())
        for child in state.get_child_asts():
            fn.apply(state.but_with(
                ast=child,
                context=fn_context,
                updated_epoch_uids=set()))
        deps = FunctionDepFactory.create_deps(state.but_with(context=fn_context))
        fn.deps_db.add_deps_for(adapters.Def(state).get_function_instance(), deps)

    @Visitor.for_ast_types(*adapters.ArgsRets.ast_types)
    def _argsrets(fn, state: State):
        if not state.get_ast().has_no_children():
            fn.apply(state.but_with(
                ast=state.first_child(),
                place=adapters.ArgsRets(state).get_node_type()))

    @Visitor.for_ast_types(*adapters.InferenceAssign.ast_types)
    def _idecls(fn, state: State):
        node = adapters.InferenceAssign(state)
        lvals = []
        for name in node.get_names():
            lvals.append(LvalIdentity(state.add_new_entity(
                name=name,
                depth=state.get_nest_depth(),
                is_let=node.get_is_let())))
        rvals = fn.apply(state.but_with_second_child())
        for lval, rval in zip(lvals, rvals):
            MoveVisitor.update_entity(state, lval, rval)

    @Visitor.for_ast_types("=")
    def _eq(fn, state: State):
        lvals = LvalMoveVisitor().apply(state.but_with_first_child())
        rights = fn.apply(state.but_with_second_child())
        for lval, rval in zip(lvals, rights):
            MoveVisitor.update_entity(state, lval, rval)

    @Visitor.for_ast_types("+=", "*=", "/=", "-=")
    def _math_eq(fn, state: State):
        fn.apply(state.but_with_first_child())
        fn.apply(state.but_with_second_child())

    @Visitor.for_ast_types("ref")
    def _ref(fn, state: State):
        epoch = state.get_entity_by_name(adapters.Ref(state).get_name())
        Validate.healthy_dependencies(state, epoch)
        return [epoch]

    @Visitor.for_ast_types(".")
    def _dot(fn, state: State):
        epoch = state.get_entity_by_name(adapters.Scope(state).get_object_name())
        Validate.healthy_dependencies(state, epoch)
        return [epoch]

    @Visitor.for_ast_types("cast")
    def _cast(fn, state: State):
        return fn.apply(state.but_with_first_child())

    # TODO: write this
    # Note: should we allow references to the moved object here? Might be
    # necessary if we want to move a pair of objects that refer to each other.
    @Visitor.for_ast_types("call")
    def _call(fn, state: State):
        node = adapters.Call(state)
        if node.is_print():
            fn.apply(state.but_with(ast=node.get_params_ast()))
            return []

        if node.is_append():
            fn.apply(state.but_with(ast=node.get_params_ast()))
            return []

        if node.is_pure_function_call():
            # F_deps = state.get_deps_of_function(node.get_function_instance())
            F_deps = fn.deps_db.lookup_deps_of(node.get_function_instance())
            if F_deps is None:
                fn.apply(state.but_with(ast=node.get_ast_defining_the_function()))
                F_deps = fn.deps_db.lookup_deps_of(node.get_function_instance())

            param_epochs = fn.apply(state.but_with(ast=node.get_params_ast()))
            for type_, epoch in zip(node.get_function_argument_type().unpack_into_parts(), param_epochs):
                if type_.restriction.is_move():
                    epoch.mark_as_gone()

            for old_epoch, new_param_epoch in zip(param_epochs, F_deps.apply_for_args(param_epochs)):
                if Validate.epoch_dependencies_are_ok(state, new_param_epoch).failed():
                    state.restore_to_healthy(new_param_epoch)
                MoveVisitor.add_epoch_uid_as_updated(state, old_epoch, new_param_epoch)

            return F_deps.apply_for_rets(param_epochs)
        else:
            print("todo: move checking with lambda/curried functions")
            param_epochs = fn.apply(state.but_with(ast=node.get_params_ast()))
            return [Entity.create_anonymous()] * len(param_epochs)

    @Visitor.for_ast_types("curry_call")
    def _curry_call(fn, state: State):
        # create a new epoch as this will return a new "entity"
        epoch = Entity.create_anonymous()
        lval = LvalIdentity(entity=epoch)
        # this new epoch should have the same dependencies as function being curried
        MoveVisitor.update_entity(state, lval, fn.apply(state.but_with_first_child())[0])

        # this new epoch should also have dependencies on each child parameter.
        lval.attribute_is_modified = True
        for rval in fn.apply(state.but_with_second_child()):
            MoveVisitor.update_entity(state, lval, rval)
        return [Entity.create_anonymous()]

    @Visitor.for_ast_types(*adapters.Typing.ast_types)
    def _decls(fn, state: State):
        node = adapters.Typing(state)
        for name in node.get_names():
            state.add_new_entity(
                name=name,
                depth=state.get_nest_depth(),
                is_let=node.get_is_let())

    @Visitor.for_ast_types(*no_assign_binary_ops, *boolean_return_ops)
    def _binop(fn, state: State):
        fn.apply(state.but_with_first_child())
        fn.apply(state.but_with_second_child())
        return [Entity.create_anonymous()]

    @Visitor.for_ast_types("!")
    def _not(fn, state: State):
        fn.apply(state.but_with_first_child())
        return [Entity.create_anonymous()]

    @Visitor.for_ast_types("params", "tuple", "curried")
    def _params(fn, state: State):
        epochs = []
        for child in state.get_all_children():
            epochs += fn.apply(state.but_with(ast=child))
        return epochs

    @Visitor.for_ast_types("while")
    def _while(fn, state: State):
        cond_state = state.but_with(
            ast=state.first_child(),
            context=state.create_block_context(),
            nest_depth=state.get_nest_depth() + 1)

        # no spreads can change in the first part of the cond, as there is no assignment
        fn.apply(cond_state.but_with_first_child())

        seq_state = state.but_with(
            ast=state.first_child().second(),
            context=state.create_block_context(),
            nest_depth=state.get_nest_depth() + 1,
            updated_epoch_uids=set(),
            exceptions=[])

        epoch_uids_updated_at_any_point: set[uuid.UUID] = set()
        fn.apply(seq_state)
        for uid in seq_state.get_updated_epoch_uids(): epoch_uids_updated_at_any_point.add(uid)
        # iteration = 0
        while seq_state.get_updated_epoch_uids():
            # iteration += 1 print(iteration)
            seq_state = seq_state.but_with(
                ast=cond_state.second_child(),
                exceptions=[],
                updated_epoch_uids=set())
            fn.apply(seq_state)
            for uid in seq_state.get_updated_epoch_uids(): epoch_uids_updated_at_any_point.add(uid)

        # need to take from seq_state and add to state for any uid which was ever
        # changed inside the while loop
        for uid in epoch_uids_updated_at_any_point:
            epoch = seq_state.get_entity_by_uid(uid)
            if Validate.epoch_dependencies_are_ok(state, epoch).failed():
                state.restore_to_healthy(epoch)
            state.add_entity(epoch)

    @Visitor.for_ast_types("if")
    def _if(fn, state: State) -> Type:
        updated_epoch_uids: set[uuid.UUID] = set()
        if_contexts: list[Context] = []
        for child in state.get_child_asts():
            context = state.create_block_context()
            if_contexts.append(context)
            fn.apply(state.but_with(
                ast=child,
                context=context,
                updated_epoch_uids=updated_epoch_uids,
                nest_depth=state.get_nest_depth() + 1))

        MoveVisitor._update_epochs_after_conditional(state, if_contexts, updated_epoch_uids)

    @staticmethod
    def _update_epochs_after_conditional(state: State, if_contexts: list[Context], updated_epoch_uids: set[uuid.UUID]):
        for uid in updated_epoch_uids:
            branch_epochs = [state.but_with(context=branch_context).get_entity_by_uid(uid)
                for branch_context in if_contexts]
            branch_epochs = [e for e in branch_epochs if e is not None]
            new_epoch_for_uid = state.get_entity_by_uid(uid).merge_dependencies_of(branch_epochs)

            if Validate.epoch_dependencies_are_ok(state, new_epoch_for_uid).failed():
                state.restore_to_healthy(new_epoch_for_uid)

            state.add_entity(new_epoch_for_uid)


    @Visitor.for_ast_types("mod")
    def _mod(fn, state: State):
        adapters.Mod(state).enter_module_and_apply(fn)

    @Visitor.for_tokens
    def _tokens(fn, state: State):
        return [Entity.create_anonymous()]

class Deps2():
    def __init__(self, argmap: dict[int, set[int]], retmap: dict[int, set[int]]) -> None:
        self.argument_dependency_map: dict[int, set[int]] = argmap
        self.return_val_depedency_map: dict[int, set[int]] = retmap

    def apply_for_args(self, params: list[Entity]) -> list[Entity]:
        new_epochs = []
        for i, param_epoch in enumerate(params):
            additional_dependencies = [params[j] for j in self.argument_dependency_map[i]]
            new_epochs.append(param_epoch.add_dependencies_on(additional_dependencies))
        return new_epochs


    def apply_for_rets(self, params: list[Entity]) -> list[Entity]:
        new_epochs = []
        for deps in self.return_val_depedency_map.values():
            epoch = Entity.create_anonymous()
            additional_dependencies = [params[i] for i in deps]
            for dep in additional_dependencies:
                # TODO: figure this out
                if dep.lifetime.is_arg() or dep.is_let:
                    epoch.add_dependencies_on([dep])
                else:
                    epoch.merge_dependencies_of([dep])
            new_epochs.append(epoch)
        return new_epochs

    def __str__(self) -> str:
        s = "Deps\n"
        for k, v in self.argument_dependency_map.items():
            s += f"{k}: {v} | "
        s += "\n"
        for k, v in self.return_val_depedency_map.items():
            s += f"{k}: {v} | "
        return s

class FunctionDepFactory():
    @staticmethod
    def create_deps(def_final_state: State):
        node = adapters.Def(def_final_state)
        arg_epochs = [def_final_state.get_entity_by_name(name) for name in node.get_arg_names()]
        ret_epochs = [def_final_state.get_entity_by_name(name) for name in node.get_ret_names()]

        arg_uid_to_index = {}
        for i, arg_epoch in enumerate(arg_epochs):
            arg_uid_to_index[arg_epoch.uid] = i

        argmap: dict[int, set[int]] = {}
        retmap: dict[int, set[int]] = {}

        arg_uids = set(epoch.uid for epoch in arg_epochs)
        for arg_epoch in arg_epochs:
            dependency_uids = set([dependency.uid for dependency in arg_epoch.dependencies]).intersection(arg_uids)
            dependency_indexes = set([arg_uid_to_index[uid] for uid in dependency_uids])
            argmap[arg_uid_to_index[arg_epoch.uid]] = dependency_indexes

        # note: need to filter out dependencies of return values on other return values
        # TODO: how to deal with returned dependencies on returned values?
        for i, ret_epoch in enumerate(ret_epochs):
            dependency_uids = set([dependency.uid for dependency in ret_epoch.dependencies]).intersection(arg_uids)
            dependency_indexes = set([arg_uid_to_index[uid] for uid in dependency_uids])
            retmap[i] = dependency_indexes

        return Deps2(argmap, retmap)


class FunctionDepsDatabase2:
    def __init__(self) -> None:
        self._map: dict[str, Deps2] = {}

    @staticmethod
    def get_function_uid_str(instance: EisenInstance):
        return instance.get_full_name()

    def lookup_deps_of(self, function_instance: EisenInstance):
        return self._map.get(FunctionDepsDatabase2.get_function_uid_str(function_instance), None)

    def add_deps_for(self, function_instance: EisenInstance, F_deps: Deps2):
        self._map[FunctionDepsDatabase2.get_function_uid_str(function_instance)] = F_deps
