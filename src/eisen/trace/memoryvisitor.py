from __future__ import annotations

import uuid
from alpaca.utils import Visitor
from alpaca.concepts import Type, Context

import eisen.adapters as adapters
from eisen.common import no_assign_binary_ops, boolean_return_ops
from eisen.common.eiseninstance import EisenInstance
from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor
from eisen.validation.validate import Validate
from eisen.trace.entity import Entity, Memory, Lval, Shadow, Personality, FunctionDB, FunctionDelta
from alpaca.clr import AST
from alpaca.concepts import Context, Module
from alpaca.concepts import AbstractException

from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor

class MemoryVisitorState(State_PostInstanceVisitor):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    # note: updated_epoch_uids are outside the context but updated inside it
    def but_with(self,
            ast: AST = None,
            context: Context = None,
            mod: Module = None,
            exceptions: list[AbstractException] = None,
            depth: int = None,
            rets: list[Entity] = None,
            args: list[Entity] = None,
            ) -> MemoryVisitorState:

        return self._but_with(
            ast=ast,
            context=context,
            mod=mod,
            exceptions=exceptions,
            depth=depth,
            rets=rets,
            args=args)

    @staticmethod
    def create_from_basestate(state: State_PostInstanceVisitor) -> MemoryVisitorState:
        """
        Create a new instance of MemoryVisitorState from any descendant of State_PostInstanceVisitor

        :param state: The State_PostInstanceVisitor instance
        :type state: State_PostInstanceVisitor
        :return: A instance of MemoryVisitorState
        :rtype: MemoryVisitorState
        """
        return MemoryVisitorState(**state._get(), depth=0, rets=None, args=None)

    def get_depth(self) -> int:
        return self.depth

    def add_memory(self, name: str, value: Memory):
        self.get_context().add_obj("memory", name, value)

    def get_memory(self, name: str) -> Memory:
        return self.get_context().get_obj("memory", name)

    def get_memories(self) -> dict[str, Memory]:
        return self.get_context().containers["memory"]

    def add_shadow(self, value: Shadow):
        self.get_context().add_obj("shadow", value.entity.uid, value)

    def get_shadow(self, uid: uuid.UUID) -> Shadow:
        return self.get_context().get_obj("shadow", uid)

    def get_shadows(self) -> dict[uuid.UUID, Shadow]:
        return self.get_context().containers["shadow"]

    def add_entity(self, name: str, value: Entity):
        self.get_context().add_obj("entity", name, value)

    def get_entity(self, name: str) -> Entity:
        return self.get_context().get_obj("entity", name)

    def get_local_entities(self) -> list[Entity]:
        return self.get_context().containers["entity"].values()

    def get_ret_entities(self) -> list[Entity]:
        return self.rets

    def get_arg_entities(self) -> list[Entity]:
        return self.args

    def update_lval(self, lval: Lval, memory: Memory):
        # TODO: this is hacky to allow us to create a shadow for an lval that is
        # a let object
        if isinstance(memory, Shadow):
            shadow = next(iter(lval.memory.shadows))
            self.update_shadow(shadow.entity.uid, memory, root=lval.trait)
            return

        # trait is not empty if we are update state of an entity
        if lval.trait:
            shadows = [self.get_shadow(s.entity.uid) for s in lval.memory.shadows]
            other_personality = Personality({ lval.trait: memory})
            for shadow in [shadow.update_personality(other_personality) for shadow in shadows]:
                self.add_shadow(shadow)
        # if trait is empty, then name is not empty, and is the name of the variable
        else:
            self.update_memory(lval.name, memory)

    def update_memory(self, name: str, with_memory: Memory):
        memory = self.get_memory(name).update_with(with_memory)
        self.add_memory(name, memory)

    def update_shadow(self, uid: uuid.UUID, with_shadow: Shadow, root: str=""):
        shadow = self.get_shadow(uid)
        self.add_shadow(shadow.update_with(with_shadow, root))

    def create_new_entity(self, name: str):
        entity = Entity(name, self.get_depth())
        self.add_entity(name, entity)

        shadow = Shadow(entity, epoch=0, faded=False, personality=Personality(memories={}))
        self.add_shadow(shadow)
        self.add_memory(name, Memory(rewrites=True, shadows=set([shadow])))

    def get_conditional_memory(self, name: str, prior_memory: Memory) -> Memory | None:
        """
        Get the memory inside a conditional branch (cond ...) or (seq ...)
        that makes up an (if ...) context

        :param name: The name of the variable.
        :type name: str
        :return: The memroy of the variable.
        :rtype: Memory
        """
        match self.get_ast().type:
            case "cond": has_return_statement = adapters.Cond(self).has_return_statement()
            case "seq": has_return_statement = adapters.Seq(self).has_return_statement()
            case _: has_return_statement = False

        if has_return_statement:
            return None

        memory = self.get_memory(name)
        memory = memory if memory is not None else prior_memory
        return memory

    def get_conditional_shadow(self, uid: uuid.UUID, prior_shadow: Shadow) -> Shadow | None:
        match self.get_ast().type:
            case "cond": has_return_statement = adapters.Cond(self).has_return_statement()
            case "seq": has_return_statement = adapters.Seq(self).has_return_statement()
            case _: has_return_statement = False

        if has_return_statement:
            return None

        shadow = self.get_shadow(uid)
        shadow = shadow if shadow is not None else prior_shadow
        return shadow


State = MemoryVisitorState

class LValMemoryVisitor(Visitor):
    def __init__(self, debug: bool = False):
        super().__init__(debug)

    def apply(self, state: State) -> list[Lval]:
        return self._route(state.get_ast(), state)

    @Visitor.for_ast_types("ref")
    def _ref(fn, state: State):
        return [Lval(name=adapters.Ref(state).get_name(),
                     memory=state.get_memory(adapters.Ref(state).get_name()),
                     trait="")]

    @Visitor.for_ast_types("lvals")
    def _lvals(fn, state: State):
        lvals = []
        for child in state.get_all_children():
            lvals += fn.apply(state.but_with(ast=child))
        return lvals

    @Visitor.for_ast_types(".")
    def _dot(fn, state: State):
        # if the attribute is a.b.c, the trait will be b.c
        return [Lval(name="",
                     memory=state.get_memory(adapters.Scope(state).get_object_name()),
                     trait=adapters.Scope(state).get_full_name().split('.', 1)[1])]

class MemoryVisitor(Visitor):
    def __init__(self, debug: bool = False):
        self.function_db = FunctionDB()
        super().__init__(debug)

    def apply(self, state: State) -> list[Memory]:
        return self._route(state.get_ast(), state)

    def run(self, state: State) -> State:
        self.apply(MemoryVisitorState.create_from_basestate(state))
        return state

    @Visitor.for_ast_types("")
    def _noop(fn, state: State):
        return

    @Visitor.for_ast_types("params")
    def _params(fn, state: State):
        memories = []
        for child in state.get_all_children():
            memories += fn.apply(state.but_with(ast=child))
        return memories

    @Visitor.for_ast_types("struct")
    def _struct(fn, state: State):
        type = state.get_defined_type(adapters.Struct(state).get_struct_name())
        print(type)
        for n, c in zip(type.component_names, type.components):
            print(" ", n, c.restriction)

        if adapters.Struct(state).has_create_ast():
            fn.apply(state.but_with(ast=adapters.Struct(state).get_create_ast()))

    @Visitor.for_ast_types("start", "prod_type")
    def _start(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_ast_types("seq")
    def _seq(fn, state: State):
        state.apply_fn_to_all_children(fn)
        for entity in state.get_local_entities():
            state.get_shadow(entity.uid).validate_dependencies_outlive_self(state)

    @Visitor.for_ast_types("rets", "args")
    def _rets(fn, state: State):
        if state.get_ast().has_no_children():
            return []
        for name in adapters.ArgsRets(state).get_names():
            state.create_new_entity(name)

    @Visitor.for_ast_types("def", "create")
    def _def(fn, state: State):
        node = adapters.Def(state)
        fn_context = state.create_isolated_context()
        fn_state = state.but_with(context=fn_context, depth=0)

        fn.apply(fn_state.but_with(ast=node.get_args_ast()))
        arg_entities = [fn_state.get_entity(name) for name in node.get_arg_names()]

        fn.apply(fn_state.but_with(ast=node.get_rets_ast()))
        ret_entities = [fn_state.get_entity(name) for name in node.get_ret_names()]

        fn.apply(fn_state.but_with(
            ast=node.get_seq_ast(),
            depth=1,
            rets=ret_entities,
            args=arg_entities))

        arg_shadows = [fn_state.get_shadow(entity.uid) for entity in arg_entities]
        ret_shadows = [fn_state.get_shadow(entity.uid) for entity in ret_entities]

        fn.function_db.add_function_delta(
            name=node.get_function_instance().get_full_name(),
            fc=FunctionDelta(arg_shadows=arg_shadows, ret_shadows=ret_shadows))
        return []

    @Visitor.for_ast_types(*no_assign_binary_ops)
    def _no_assign_binary_ops(fn, state: State):
        pass

    @Visitor.for_ast_types("ref")
    def _ref(fn, state: State):
        node = adapters.Ref(state)
        # kxt debug
        if node.get_name() == "p2":
            entity = state.get_entity("p2")
            print(state.get_shadow(entity.uid))

        return [state.get_memory(node.get_name())]

    @Visitor.for_ast_types(".")
    def _dot(fn, state: State):
        node = adapters.Scope(state)
        fn.apply(state.but_with_first_child())

        print(state.get_returned_type())
        # raise Exception("TODO: need to make sure this works with let/var types")


    @Visitor.for_ast_types("let")
    def _let(fn, state: State):
        node = adapters.Decl(state)
        for name in node.get_names():
            state.create_new_entity(name)

    @Visitor.for_ast_types("mut", "val", "nil?")
    def _vars(fn, state: State):
        node = adapters.Decl(state)
        for name in node.get_names():
            state.add_memory(name, Memory(rewrites=True, shadows=set()))

    @Visitor.for_ast_types("=")
    def _eq(fn, state: State):
        node = adapters.Assignment(state)
        lvals = LValMemoryVisitor().apply(state.but_with_first_child())
        rvals = fn.apply(state.but_with_second_child())

        for lval, rval in zip(lvals, rvals):
            state.update_lval(lval, rval)

    # TODO: why does this return a shadow and not a memory?
    @Visitor.for_ast_types("call")
    def _call(fn, state: State):
        node = adapters.Call(state)
        # print("call to", node.get_function_name())
        delta = fn.function_db.get_function_delta(node.get_function_instance().get_full_name())
        if fn.function_db is None:
            fn.apply(state.but_with(asl=node.get_ast_defining_the_function()))
            delta = fn.function_db.get_function_delta(node.get_function_instance().get_full_name())

        # build the index to remap args to params
        arg_uids = [s.entity.uid for s in delta.arg_shadows]
        param_memories = fn.apply(state.but_with_second_child())
        index = {}
        for uid, memory in zip(arg_uids, param_memories):
            index[uid] = memory

        arg_shadows = [s.remap_via_index(index) for s in delta.arg_shadows]
        for memory, update_with_shadow in zip(param_memories, arg_shadows):
            for shadow in memory.shadows:
                state.update_shadow(shadow.entity.uid, update_with_shadow)

        shadows = [s.remap_via_index(index) for s in delta.ret_shadows]
        return shadows

    @Visitor.for_ast_types("cond")
    def _cond(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_ast_types("if")
    def _if(fn, state: State) -> Type:
        branch_states: list[state] = []
        for child in state.get_child_asts():
            branch_state = state.but_with(
                ast=child,
                context=state.create_block_context(),
                depth=state.get_depth() + 1)

            branch_states.append(branch_state)
            fn.apply(branch_state)

        MemoryVisitor.merge_realities_after_conditional(state, branch_states)

    @staticmethod
    def all_updated_memories(state: State, branch_states: list[State]):
        updated_memories: set[str] = set()
        for branch_state in branch_states:
            for key in branch_state.get_memories():
                if key in state.get_memories():
                    updated_memories.add(key)
        return updated_memories

    @staticmethod
    def all_updated_shadows(state: State, branch_states: list[State]) -> set[uuid.UUID]:
        updated_shadows: set[uuid.UUID] = set()
        for branch_state in branch_states:
            for key in branch_state.get_shadows():
                if key in state.get_shadows():
                    updated_shadows.add(key)
        return updated_shadows

    @staticmethod
    def merge_realities_after_conditional(state: State, branch_states: list[State]):
        updated_memories_names = MemoryVisitor.all_updated_memories(state, branch_states)
        new_memories = []
        for name in updated_memories_names:
            prior_memory = state.get_memory(name)

            # update set contains the individual memories from each branch reality
            update_set = [s.get_conditional_memory(name, prior_memory) for s in branch_states]
            update_set = [m for m in update_set if m is not None]

            if not MemoryVisitor.if_statement_is_exhaustive(state):
                update_set.append(prior_memory)
            new_memories.append((name, Memory.merge_all(memories=update_set)))

        updated_shadow_uids = MemoryVisitor.all_updated_shadows(state, branch_states)
        new_shadows = []
        for uid in updated_shadow_uids:
            prior_shadow = state.get_shadow(uid)

            update_set = [s.get_conditional_shadow(uid, prior_shadow) for s in branch_states]
            update_set = [s for s in update_set if s is not None]

            if not MemoryVisitor.if_statement_is_exhaustive(state):
                update_set.append(prior_shadow)
            new_shadows.append(Shadow.merge_all(update_set))

        # actually change the memories/shadows. note we don't update because
        # the prior state of each needs to be overwritten.
        for name, memory in new_memories:
            state.add_memory(name, memory)

        for shadow in new_shadows:
            state.add_shadow(shadow)

    @staticmethod
    def if_statement_is_exhaustive(state: State) -> bool:
        if state.get_all_children()[-1].type == "seq":
            return True

    @Visitor.for_ast_types("return")
    def _return(fn, state: State):
        for entity in state.get_ret_entities():
            shadow = state.get_shadow(entity.uid)
            shadow.validate_dependencies_outlive_self(state)

        # TODO: should check final state of returns
        return

    @Visitor.for_tokens
    def _tokens(fn, state: State):
        return [Memory(rewrites=True, shadows=set())]


class AttributeVisitor:
    @staticmethod
    def _ref(state: State) -> set[Shadow]:
        memory = state.get_memory(adapters.Ref(state).get_name())
        return memory.shadows

    @staticmethod
    def _dot(state: State) -> tuple[set[Shadow], str, bool]:
        if state.get_ast() == "ref":
            return AttributeVisitor._ref(state.but_with_first_child()), "", True

        parents, trait, let_sequence = AttributeVisitor._dot(state.but_with_first_child())

        if let_sequence == False:
            memories = [s.personality.get_memory(trait) for s in parents]
            # TODO: what to do here

        if state.get_returned_type().restriction.is_let():
            if trait:
                return parents, trait + "." + state.second_child().value, True
            return parents, state.second_child().value, True

        if trait:
            trait = trait + "." + state.second_child().value
        else:
            trait = state.second_child().value
        return parents, trait, False
