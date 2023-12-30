
from __future__ import annotations

import eisen.adapters as adapters
from eisen.trace.entity import Trait
from eisen.trace.memory import Memory, Impression, MemorableSet
from eisen.trace.lval import Lval

from eisen.state.memoryvisitorstate import MemoryVisitorState
from eisen.validation.validate import Validate

State = MemoryVisitorState
class AttributeVisitor:
    @staticmethod
    def _ref(state: State) -> list[Memory]:
        memory = state.get_memory(adapters.Ref(state).get_name())
        Validate.memory_dependencies_havent_moved_away(state, memory)
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
    def _form_new_impressions(state: State, memories: list[Memory], trait: Trait) -> list[Memory]:
        new_memories = []
        for m in memories:
            new_memories.append(Memory(
                rewrites=True,
                impressions=MemorableSet.create_over([Impression(
                    i.shadow, i.root.join(trait), i.place) for i in m.impressions]),
                depth=state.get_depth()))
        return new_memories

    @staticmethod
    def get_memories(state: State) -> list[Memory]:
        memories, trait, ownership_change = AttributeVisitor._dot(state)
        # need to flush here to resolve to the objects themselves
        if ownership_change:
            memories = AttributeVisitor._resolve_memories_during_owner_switch(state, trait, memories)
            trait = Trait()

        return AttributeVisitor._form_new_impressions(state, memories, trait)

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
