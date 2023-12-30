from __future__ import annotations
from dataclasses import dataclass
import uuid

import eisen.adapters as adapters
from eisen.state.memoryvisitorstate import MemoryVisitorState
from eisen.trace.entity import Trait
from eisen.trace.memory import Memory
from eisen.trace.shadow import Shadow, Personality
from eisen.trace.entanglement import Entanglement

@dataclass
class ConditionalMemory():
    """
    This represents a memory defined outside of a conditional context, that may have
    been modified inside the conditional context
    """

    memory: Memory | None
    branch_id: uuid.UUID

    def get_dependency_depths_set(self) -> set[int]:
        """
        Return a set of the depths of all impressions of this memory
        """
        if self.memory is None: return None
        return set([i.shadow.entity.depth for i in self.memory.impressions])

    def get_memory(self, with_entanglement: bool):
        if self.memory is None: return None
        if with_entanglement: return self.memory.with_entanglement(Entanglement(self.branch_id))
        else: return self.memory

    def get_function_set(self) -> set:
        if self.memory is None: return None
        return set([f.function_instance for f in self.memory.functions._functions])

@dataclass
class ConditionalContext():
    memory_name: str
    conditional_memories: list[ConditionalMemory]
    has_possible_entanglement: bool = False

    def check_for_entanglement(self) -> bool:
        """
        Returns true of the [memories] contain a superposition
        """
        if len(self.conditional_memories) < 2: return False # TODO: will this ever get called?

        # case for impressions
        depth_sets = [memory.get_dependency_depths_set() for memory in self.conditional_memories]
        impressions_entangled = not all(sets == depth_sets[0] for sets in depth_sets if sets is not None)

        # case for functions
        function_sets = [memory.get_function_set() for memory in self.conditional_memories]
        functions_entangled = not all(sets == function_sets[0] for sets in function_sets if sets is not None)

        self.has_possible_entanglement = impressions_entangled or functions_entangled
        return self.has_possible_entanglement

    def get_memories(self, should_use_entanglement: bool) -> list[Memory]:
        memories = [cm.get_memory(should_use_entanglement)
                    for cm in self.conditional_memories]
        return [m for m in memories if m is not None]

@dataclass
class FusionContext():
    conditional_contexts: list[ConditionalContext]

    def has_entanglement(self):
        possible_entanglements = [context.check_for_entanglement() for context in self.conditional_contexts]
        return possible_entanglements.count(True) > 1


State = MemoryVisitorState
class RealityFuser:
    """
    After conditional branching, the state of shadows/memories within each branch of the
    conditional may diverge. The process of combinding the state after each branch
    back to a "central timeline" is called fusing.

    The RealityFuser takes the original state [state] before the conditional branching
    as well as the states [branch_states] from each branch at the end of each conditonal
    branch.

    Definition [Fusing]: For a given value x: T, fusing is the process of taking S: set[T]
    where S is the set of all possible end values of x after the conditional branching,
    and computing x', which should be the source-of-truth value of x in the main
    timeline, after the conditional branching has occured.

    In other words, fusing can be represented as the function, given x: T prior to
    conditional divergence,

        Fusing := S(x): set[T]  -> x': T

    """

    def __init__(self, origin_state: State, branch_states: list[State]) -> None:
        """
        Create a new RealityFuser for an (if ...) AST

        :param origin_state: The state prior to any conditional branching
        :type origin_state: State
        :param branch_states: The state for each branch after it has been run
        :type branch_states: list[State]
        """
        self.origin_state = origin_state
        self.branch_states = branch_states

    def number_of_realities(self) -> int:
        """
        :return: The number of realties (branches) of a conditional, including the default reality
        :rtype: int
        """
        return len(self.branch_states) + (0 if self.branching_is_exhaustive() else 1)

    def fuse_memory_with_entanglements(self, names: list[str]):
        reality_ids = [uuid.uuid4() for i in range(self.number_of_realities())]
        fusion_context = FusionContext([])

        # init the fusion context
        for name in names:
            prior_memory = self.origin_state.get_memory(name)

            # update set contains the individual memories from each branch reality
            update_set = [self.get_memory_in_branch(branch, name, prior_memory)
                        for branch in self.branch_states]
            if not self.branching_is_exhaustive():
                update_set.append(prior_memory)
            conditional_memories = [ConditionalMemory(memory, id) for memory, id in zip(update_set, reality_ids)]
            fusion_context.conditional_contexts.append(ConditionalContext(name, conditional_memories))

        is_entangled = fusion_context.has_entanglement()

        tuples = []
        for conditional_context in fusion_context.conditional_contexts:
            memory = RealityFuser.fuse_memories_from_different_realities(
                memories=conditional_context.get_memories(should_use_entanglement=is_entangled))
            tuples.append((conditional_context.memory_name, memory))

        return tuples

    @staticmethod
    def branch_has_return_statement(branch: State) -> bool:
        match branch.get_ast().type:
            case "cond": return adapters.Cond(branch).has_return_statement()
            case "seq": return adapters.Seq(branch).has_return_statement()
            case _: return False

    def get_memory_in_branch(self, branch: State, name: str, prior_memory: Memory) -> Memory | None:
        """
        Get the memory inside a conditional branch (cond ...) or (seq ...)
        that makes up an (if ...) context

        :param name: The name of the variable.
        :type name: str
        :return: The memory of the variable.
        :rtype: Memory
        """
        # TODO: this logic may not be accurate
        # if a branch has a return statement, then there is no memory at the end of the branch,
        # provided that prior_shadow is not of a return/argument value
        if RealityFuser.branch_has_return_statement(branch) and prior_memory and prior_memory.depth > 0:
            return None

        memory = branch.get_memory(name)
        memory = memory if memory is not None else prior_memory
        return memory

    def get_branched_trait_memory_of_shadow(self, branch: State, uid: uuid.UUID, trait: Trait, prior_shadow: Shadow) -> Memory | None:
        """
        For the shadow with [uid] after the conditonal [branch], get the memory of it's [trait],
        and if there is no shadow in the branch, return the memory of the [prior_shadow]'s [trait].
        """
        # TODO: this logic may not be accurate
        # if a branch has a return statement, then there is no memory at the end of the branch,
        # provided that prior_shadow is not of a return/argument value
        if RealityFuser.branch_has_return_statement(branch) and prior_shadow and prior_shadow.entity.depth > 0:
            return None

        shadow = branch.get_shadow(uid)
        shadow = shadow if shadow is not None else prior_shadow
        return shadow.personality.memories.get(trait)

    def all_updated_memory_names(self) -> set[str]:
        """
        Returns a set of all memory names which may have been updated
        in any branch of the conditional.
        """
        updated_memories: set[str] = set()
        for branch_state in self.branch_states:
            for key in branch_state.get_memories():
                if self.origin_state.get_memory(key):
                    updated_memories.add(key)
        return updated_memories

    def all_updated_shadows(self) -> set[uuid.UUID]:
        """
        Returns a set of uuids for shadows which may have been updated in
        any branch of the conditional.
        """
        updated_shadows: set[uuid.UUID] = set()
        for branch_state in self.branch_states:
            for key in branch_state.get_shadows():
                if self.origin_state.get_shadow(key):
                    updated_shadows.add(key)
        return updated_shadows

    def all_updated_traits(self, uid: uuid.UUID) -> set[Trait]:
        """
        Returns a set of all traits of a given shadow specified by [uid] which
        may have been updated in any branch of the conditional.
        """
        original_shadow = self.origin_state.get_shadow(uid)
        traits: set[Trait] = set()
        for branch_state in self.branch_states:
            shadow_in_branch = branch_state.get_shadows().get(uid)
            if shadow_in_branch is not None:
                for trait, memory in shadow_in_branch.personality.memories.items():
                    if (memory.impressions != original_shadow.personality.get_memory(trait).impressions
                    and not RealityFuser.branch_has_return_statement(branch_state)):
                        traits.add(trait)
        return traits

    @staticmethod
    def fuse_memories_from_different_realities(memories: list[Memory]) -> Memory:
        return Memory.merge_all(
            memories=memories,
            rewrites=True)

    @staticmethod
    def fuse_shadows_from_different_realities(shadows: list[Shadow]) -> Shadow:
        return Shadow.merge_all(shadows=shadows)

    @staticmethod
    def fuse_together(shadows_or_memories_from_different_realities: list[Shadow] | list[Memory]):
        match shadows_or_memories_from_different_realities[0]:
            case Shadow(): return RealityFuser.fuse_shadows_from_different_realities(
                shadows=shadows_or_memories_from_different_realities)

            case Memory(): return RealityFuser.fuse_memories_from_different_realities(
                memories =shadows_or_memories_from_different_realities)

    @staticmethod
    def collect_paralleled_shadows_or_memories_from_different_outcomes(pos: int, outcomes: list[list[Shadow | Memory]]) -> list[Shadow] | list[Memory]:
        """
        The following transformation:
            pos:      0    1    2
        outcome 1:   S_1  S_2  M_3
        outcome 2:   S_4  S_5  M_6
        outcome 3:   S_7  S_8  M_9

        Returns for 1:
            [ S_2, S_5, S_8 ]
        """
        return [outcome[pos] for outcome in outcomes]

    @staticmethod
    def fuse_outcomes_together(outcomes: list[list[Shadow | Memory]]):
        """
        An outcome is a list of shadows or memories that get returned. Therefore [outcomes]
        is a list of these.
        """
        parallels = range(len(outcomes[0]))
        return [RealityFuser.fuse_together(
            RealityFuser.collect_paralleled_shadows_or_memories_from_different_outcomes(pos, outcomes))
            for pos in parallels]

    def get_all_fused_memories(self) -> list[tuple[str, Memory]]:
        """
        Fuse all updated memories after the conditional and return a tuple of the
        (memory.name, memory) for each fused memory.
        """
        updated_memories_names = self.all_updated_memory_names()
        return self.fuse_memory_with_entanglements(updated_memories_names)

    def fuse_memory_for_trait(self, trait: Trait, prior_shadow: Shadow) -> Memory:
        """
        Fuse the memory for a specific [trait] which may belong to the [prior_shadow].
        The correct shadow in each conditional branch is determined by the entity.uid
        of the [prior_shadow].

        Returns the fused memory.
        """
        update_set = [self.get_branched_trait_memory_of_shadow(
            branch, prior_shadow.entity.uid, trait, prior_shadow) for branch in self.branch_states]
        update_set = [s for s in update_set if s is not None]
        return Memory.merge_all(
            memories=update_set,
            rewrites=self.branching_is_exhaustive())

    def fuse_personality_for(self, uid: uuid.UUID) -> Personality:
        """
        Fuse the personality for a shadow specified by [uid] componentwise by trait.

        Returns the fused personality.
        """
        prior_shadow = self.origin_state.get_shadow(uid)
        updated_traits = self.all_updated_traits(uid)
        return Personality({
            trait: self.fuse_memory_for_trait(trait, prior_shadow)
                for trait in updated_traits})

    def get_all_fused_personalities(self) -> list[tuple[uuid.UUID, Personality]]:
        """
        Fuse personalities for all shadows which may have been changed during
        the conditional branching.

        Returns a tuple (uid, personality) where 'uid' is the uid of the changed
        shadow, and 'personality' is the fused personality.
        """
        updated_shadow_uids = self.all_updated_shadows()
        return [(uid, self.fuse_personality_for(uid))
                for uid in updated_shadow_uids]

    def fuse_realities_after_conditional(self):
        """
        Apply all necessary fusing after a branching conditional to bring all
        types back to a single value for the main timeline to proceed.
        """
        for name, memory in self.get_all_fused_memories():
            self.origin_state.add_memory(name, memory)
        for uid, personality in self.get_all_fused_personalities():
            self.origin_state.update_personality(uid, personality)

    def branching_is_exhaustive(self) -> bool:
        """
        :return: True if the branching is exhaustive
        :rtype: bool
        """
        if self.origin_state.get_all_children()[-1].type == "seq":
            return True
        return False

    def all_updated_memories(self) -> set[Memory]:
        """
        Returns a set of all memory names which may have been updated
        in any branch of the conditional.
        """
        updated_memories: set[Memory] = set()
        for name in self.all_updated_memory_names():
            for branch_state in self.branch_states:
                updated_memories.add(branch_state.get_memory(name))
        return updated_memories
