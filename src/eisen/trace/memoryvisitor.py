from __future__ import annotations

import uuid
from alpaca.utils import Visitor
from alpaca.concepts import Type, Context

import eisen.adapters as adapters
from eisen.common import no_assign_binary_ops, boolean_return_ops
from eisen.common.eiseninstance import EisenInstance
from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor
from eisen.validation.validate import Validate
from eisen.trace.entity import Entity, Memory, Lval, Shadow, Personality, FunctionDB, FunctionDelta, Impression, Trait, Angel
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
            function_base_context = None,
            mod: Module = None,
            exceptions: list[AbstractException] = None,
            depth: int = None,
            rets: list[Entity] = None,
            args: list[Entity] = None,
            angels: list[Angel] = None
            ) -> MemoryVisitorState:

        return self._but_with(
            ast=ast,
            context=context,
            function_base_context=function_base_context,
            mod=mod,
            exceptions=exceptions,
            depth=depth,
            rets=rets,
            args=args,
            angels=angels
            )

    @staticmethod
    def create_from_basestate(state: State_PostInstanceVisitor) -> MemoryVisitorState:
        """
        Create a new instance of MemoryVisitorState from any descendant of State_PostInstanceVisitor

        :param state: The State_PostInstanceVisitor instance
        :type state: State_PostInstanceVisitor
        :return: A instance of MemoryVisitorState
        :rtype: MemoryVisitorState
        """
        return MemoryVisitorState(**state._get(), depth=0,
                                  function_base_context=None,
                                  rets=None, args=None, angels=None)

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
            shadow = next(iter(lval.memory.impressions)).shadow
            self.update_shadow(shadow.entity.uid, memory, root=lval.trait)
            return

        # trait is not empty if we are update state of an entity
        if lval.trait:
            for impression in lval.memory.impressions:
                other_personality = Personality( { lval.trait: memory })

                # get the current shadow
                current_shadow_to_update = self.get_shadow(impression.shadow.entity.uid)
                new_shadow = current_shadow_to_update\
                    .update_personality(other_personality, impression.root, depth=self.get_depth())
                self.add_shadow(new_shadow)
        else:
            self.update_memory(lval.name, memory)

    def update_memory(self, name: str, with_memory: Memory):
        memory = self.get_memory(name).update_with(with_memory)
        self.add_memory(name, memory)

    def update_shadow(self, uid: uuid.UUID, with_shadow: Shadow, root: Trait=Trait()):
        shadow = self.get_shadow(uid)
        self.add_shadow(shadow.update_with(with_shadow, root, depth=self.get_depth()))

    def add_trait(self, shadow: Shadow, trait: Trait, memory: Memory):
        other_personality = Personality( { trait: memory })
        new_shadow = shadow.update_personality(other_personality, root=Trait(), depth=self.get_depth())
        self.add_shadow(new_shadow)

    def update_personality(self, uid: uuid.UUID, other_personality: Personality):
        new_shadow = self.get_shadow(uid).update_personality(other_personality, root=Trait(), depth=self.get_depth())
        self.add_shadow(new_shadow)

    def _recognize_entity(self, entity: Entity) -> Shadow:
        self.add_entity(entity.name, entity)
        shadow = Shadow(entity, epoch=0, faded=False, personality=Personality(memories={}))
        self.add_shadow(shadow)
        return shadow

    def resolve_angel_into_memories(self, angel: Angel, index: dict[uuid.UUID, Memory]) -> list[Memory]:
        original_memory = index.get(angel.entity.uid)

        memories = []
        for i in original_memory.impressions:
            shadow = self.get_shadow(i.shadow.entity.uid)
            m = shadow.personality.get_memory(i.root.join(angel.trait))
            if m is None:
                m = self.create_new_angel_memory(i.root.join(angel.trait), shadow.entity)
                self.add_trait(shadow, trait=i.root.join(angel.trait), memory=m)
            memories.append(m)
        return memories

    def create_new_entity(self, name: str):
        entity = Entity(name, self.get_depth())
        shadow = self._recognize_entity(entity)
        self.add_memory(entity.name, Memory(
            rewrites=True,
            impressions=set([Impression(shadow=shadow, root=Trait(), place=self.get_line_number())])))

    def create_new_angel(self, entity_attribute: Trait, entity: Entity) -> Shadow:
        angel = Angel(trait=entity_attribute, entity=entity)
        self.angels.append(angel)
        return self.but_with(context=self.get_function_base_context())._recognize_entity(angel)

    def create_new_angel_memory(self, trait: Trait, entity: Entity) -> Memory:
        angel_shadow = self.create_new_angel(trait, entity)
        return Memory(
            rewrites=True,
            impressions=set([Impression(
                shadow=angel_shadow,
                root=Trait(),
                place=-1)]))


    def get_function_base_context(self) -> Context:
        return self.function_base_context

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

    def get_conditional_trait_memory(self, uid: uuid.UUID, trait: Trait, prior_shadow: Shadow) -> Memory | None:
        match self.get_ast().type:
            case "cond": has_return_statement = adapters.Cond(self).has_return_statement()
            case "seq": has_return_statement = adapters.Seq(self).has_return_statement()
            case _: has_return_statement = False

        if has_return_statement:
            return None

        shadow = self.get_shadow(uid)
        shadow = shadow if shadow is not None else prior_shadow
        return shadow.personality.memories.get(trait)


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
                     trait=Trait())]

    @Visitor.for_ast_types("lvals")
    def _lvals(fn, state: State):
        lvals = []
        for child in state.get_all_children():
            lvals += fn.apply(state.but_with(ast=child))
        return lvals

    @Visitor.for_ast_types(".")
    def _dot(fn, state: State):
        # if the attribute is a.b.c, the trait will be b.c
        return AttributeVisitor.get_lvals(state)

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
        # print(node.get_function_name())
        fn_context = state.create_isolated_context()
        fn_state = state.but_with(context=fn_context, function_base_context=fn_context, depth=0)

        fn.apply(fn_state.but_with(ast=node.get_args_ast()))
        arg_entities = [fn_state.get_entity(name) for name in node.get_arg_names()]

        fn.apply(fn_state.but_with(ast=node.get_rets_ast()))
        ret_entities = [fn_state.get_entity(name) for name in node.get_ret_names()]

        angels: list[Angel] = []
        fn.apply(fn_state.but_with(
            ast=node.get_seq_ast(),
            depth=1,
            rets=ret_entities,
            args=arg_entities,
            angels=angels))

        arg_shadows = [fn_state.get_shadow(entity.uid) for entity in arg_entities]
        ret_shadows = [fn_state.get_shadow(entity.uid) for entity in ret_entities]
        angel_shadows = {}

        for angel in angels:
            angel_shadows[angel.uid] = fn_state.get_shadow(angel.uid)

        fn.function_db.add_function_delta(
            name=node.get_function_instance().get_full_name(),
            fc=FunctionDelta(arg_shadows=arg_shadows,
                             ret_shadows=ret_shadows,
                             angels=angels,
                             angel_shadows=angel_shadows))

        # print("finished for ", node.get_function_name())
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
        if node.get_name() == "p":
            entity = state.get_entity("p")
            print(state.get_shadow(entity.uid))
        if node.get_name() == "n2":
            entity = state.get_entity("n2")
            print(state.get_shadow(entity.uid))
        if node.get_name() == "a":
            print(state.get_memory("a"))

        return [state.get_memory(node.get_name())]

    @Visitor.for_ast_types(".")
    def _dot(fn, state: State):
        memories = AttributeVisitor.get_memories(state)
        return memories


    @Visitor.for_ast_types("let")
    def _let(fn, state: State):
        node = adapters.Decl(state)
        for name in node.get_names():
            state.create_new_entity(name)

    @Visitor.for_ast_types("mut", "val", "nil?")
    def _vars(fn, state: State):
        node = adapters.Decl(state)
        for name in node.get_names():
            state.add_memory(name, Memory(rewrites=True, impressions=set()))

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
        if delta is None:
            fn.apply(state.but_with(ast=node.get_ast_defining_the_function()))
            delta = fn.function_db.get_function_delta(node.get_function_instance().get_full_name())

        # build the index to remap args to params
        arg_uids = [s.entity.uid for s in delta.arg_shadows]
        param_memories = fn.apply(state.but_with_second_child())
        index: dict[uuid.UUID, Memory] = {}
        for uid, memory in zip(arg_uids, param_memories):
            index[uid] = memory

        for angel in delta.angels:
            possible_argument_trait_memory = state.resolve_angel_into_memories(angel, index)
            index[angel.uid] = possible_argument_trait_memory

        arg_shadows = [s.remap_via_index(index) for s in delta.arg_shadows]

        angel_shadows = [s.remap_via_index(index) for s in delta.angel_shadows.values()]
        angel_shadow_dict = { s.entity.uid: s for s in angel_shadows }
        for angel in delta.angels:
            possible_argument_trait_memory = state.resolve_angel_into_memories(angel, index)
            for m in possible_argument_trait_memory:
                for i in m.impressions:
                    state.update_shadow(i.shadow.entity.uid, angel_shadow_dict.get(angel.uid), root=i.root)

        for memory, update_with_shadow in zip(param_memories, arg_shadows):
            for impression in memory.impressions:
                state.update_shadow(impression.shadow.entity.uid, update_with_shadow, root=impression.root)

        # TODO: hotfix to be removed
        if len(node.get_function_return_type().unpack_into_parts()) > 0 and not ( node.get_function_return_type().unpack_into_parts()[0].restriction.is_new_let()
                                                                             or node.get_function_return_type() == state.get_void_type()):
            print(node.get_function_name())
            raise Exception()


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
    def all_updated_traits(state: State, uid: uuid.UUID, branch_states: list[State]) -> set[Trait]:
        traits = set()
        for branch_state in branch_states:
            shadow_in_branch = branch_state.get_shadows().get(uid)
            if shadow_in_branch is not None:
                for trait, memory in shadow_in_branch.personality.memories.items():
                    if memory.depth > state.get_depth():
                        traits.add(trait)
        return traits

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

        # NEED to do it by personality!
        updated_shadow_uids = MemoryVisitor.all_updated_shadows(state, branch_states)
        new_personalities = []
        for uid in updated_shadow_uids:
            prior_shadow = state.get_shadow(uid)
            new_personality = Personality({})
            updated_traits = MemoryVisitor.all_updated_traits(state, uid, branch_states)
            for trait in updated_traits:
                update_set = [s.get_conditional_trait_memory(uid, trait, prior_shadow) for s in branch_states]
                update_set = [s for s in update_set if s is not None]

                new_memory = Memory.merge_all(memories=update_set)
                if MemoryVisitor.if_statement_is_exhaustive(state):
                    new_memory.rewrites = True
                else:
                    new_memory.rewrites = False

                new_memory.depth = state.get_depth() + 1
                new_personality.memories[trait] = new_memory
            new_personalities.append((uid, new_personality))
            # new_shadows.append(Shadow.merge_all(update_set, depth=state.get_depth()+1))

        # actually change the memories/shadows. note we don't update because
        # the prior state of each needs to be overwritten.
        for name, memory in new_memories:
            state.add_memory(name, memory)

        for uid, personality in new_personalities:
            state.update_personality(uid, personality)

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
        return [Memory(rewrites=True, impressions=set())]


class AttributeVisitor:
    @staticmethod
    def _ref(state: State) -> list[Memory]:
        memory = state.get_memory(adapters.Ref(state).get_name())
        return [memory]

    @staticmethod
    def _perform_owner_switch(state: State, i: Impression, trait: Trait) -> Memory:
        """
        (see _resolve_memories_during_owner_switch)
        Let i be some impression inside the memory X. This is the impression of some
        shadow of some entity. But as the given trait induced an onwership switch,
        if E is the entity, then E.b.c must resolve to b'.c for any b' which may
        be referenced by the memory E has at E.b

        Therefore we must:
            1. Obtain the current shadow of E
            2. Get the memory at E.b with respect to the current shadow of E. The entities
               behind the shadows of this new memory are now the new owners of the memory
               referenced by .c (i.e. the entities which cast these shadows are b').

        :param state: The current state
        :type state: State
        :param i: A given impression or a which will be used to resolve b'
        :type i: Impression
        :param trait: The trait to be resolved
        :type trait: Trait
        :rtype: Impression
        """
        current_shadow = state.get_shadow(i.shadow.entity.uid)
        existing_memory = current_shadow.personality.get_memory(i.root.join(trait))
        if existing_memory:
            return existing_memory

        if state.get_returned_type().restriction.is_primitive():
            return None

        # no memory, need to add a memory of an angel
        new_memory = state.create_new_angel_memory(i.root.join(trait), current_shadow.entity)

        state.add_trait(current_shadow, trait=i.root.join(trait), memory=new_memory)
        return new_memory

    @staticmethod
    def _resolve_memories_during_owner_switch(state: State, trait: Trait, current_memories: list[Memory]) -> list[Memory]:
        """
        Given the attribute sequence X.b.c, where X.b has var restriction, there
        must exist some external entity b' which is the proper owner of 'c'. Therefore
        X.b.c. must actually resolve to b'.c for proper ownership.

        For a given impression X having the trait .b.c, an ownership, and given that
        an ownership switch occurs from the owner of X to b', it is necessary to:
            1. Obtain the memory X.b
            2. Identify the current shadow of any entity b' which may be referenced in the memory X.b
            3. Return the memory of b'.c

        :param state: The current state
        :type state: State
        :param trait: The trait which is currently being resolved and which induces an ownership switch
        :type trait: Trait
        :param current_memories: The list of current_memories
        :type current_memories: list[Memory]
        :return: A list of memories after resolving the owner switch
        :rtype: list[Memory]
        """
        unlocked_memories = []
        for memory in current_memories:
            unlocked_memories += [AttributeVisitor._perform_owner_switch(state, i, trait) for i in memory.impressions]
        unlocked_memories = [m for m in unlocked_memories if m]
        return unlocked_memories

    @staticmethod
    def _has_ownership_change(state: State) -> bool:
        return not state.get_restriction().is_let() and not state.get_restriction().is_primitive()

    @staticmethod
    def _dot(state: State) -> tuple[list[Memory], str, bool]:
        if state.get_ast().type == "ref":
            return AttributeVisitor._ref(state), Trait(), False

        parents, trait, ownership_change = AttributeVisitor._dot(state.but_with_first_child())

        if ownership_change:
            return AttributeVisitor._resolve_memories_during_owner_switch(state, trait, parents), Trait(state.second_child().value), False

        trait = trait.join(Trait(state.second_child().value))
        return parents, trait, AttributeVisitor._has_ownership_change(state)

    @staticmethod
    def _form_new_impressions(memories: list[Memory], trait: Trait) -> list[Memory]:
        new_memories = []
        for m in memories:
            new_memories.append(Memory(rewrites=True,
                impressions=set([Impression(
                i.shadow, i.root.join(trait), i.place) for i in m.impressions])))
        return new_memories

    @staticmethod
    def get_memories(state: State) -> list[Memory]:
        memories, trait, ownership_change = AttributeVisitor._dot(state)
        # need to flush here to resolve to the objects themselves
        if ownership_change:
            memories = AttributeVisitor._resolve_memories_during_owner_switch(state, trait, memories)
            trait = Trait()

        return AttributeVisitor._form_new_impressions(memories, trait)

    @staticmethod
    def get_lvals(state: State) -> list[Lval]:
        memories, trait, _ = AttributeVisitor._dot(state)

        # no need to flush here as we modify the actual object

        lvals = []
        for memory in memories:
            lvals.append(Lval(name="",
                     memory=memory,
                     trait=trait))
        return lvals
