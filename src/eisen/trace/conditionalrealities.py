from __future__ import annotations
from dataclasses import dataclass, field
import uuid

import eisen.adapters as adapters
from eisen.state.memoryvisitorstate import MemoryVisitorState
from eisen.trace.entity import Trait
from eisen.trace.memory import Memory
from eisen.trace.shadow import Shadow, Personality
from eisen.trace.entity import Entity
from eisen.trace.entanglement import Entanglement


@dataclass
class AbstractConditionalContext():
    def __post_init__(self):
        self._possible_entanglement: None = None


@dataclass
class ShadowContext(AbstractConditionalContext):
    entity: Entity
    shadows: list[Shadow | None]
    branch_ids: list[uuid.UUID]
    entangled_traits: dict[Trait, ConditionalContext] | None = field(default_factory=dict)

    def _check_entanglement_of(self, trait: Trait):
        memories = [shadow.personality.get_memory(trait) if shadow else None
                    for shadow in self.shadows]

        # create a conditional context for the memories for this trait accross all branches
        # of the conditional
        context = ConditionalContext(
            memory_name=self.entity.name + "." + str(trait),
            conditional_memories=[ConditionalMemory(memory, id)
                                  for memory, id in zip(memories, self.branch_ids)])

        # we only need to record the conditional_context if there is a possible entanglement
        if context.check_for_entanglement(): self.entangled_traits[trait] = context

    def _all_traits(self):
        return set([trait for shadow in self.shadows if shadow is not None
                    for trait in shadow.personality.get_all_traits()])

    def check_for_entanglement(self) -> bool:
        if self._possible_entanglement is not None: return self._possible_entanglement
        for trait in self._all_traits(): self._check_entanglement_of(trait)
        self._possible_entanglement = len(self.entangled_traits) > 0
        return self._possible_entanglement

    def _get_fused_memory_without_entanglement(self, trait: Trait) -> list[Memory]:
        memories = [shadow.personality.get_memory(trait) for shadow in self.shadows]
        return Memory.merge_all([m for m in memories if m is not None], rewrites=True)

    def get_fused_personality(self, is_entangled: bool) -> Personality:
        trait_dict: dict[Trait, Memory] = {}
        for trait in self._all_traits():
            if trait in self.entangled_traits:
                conditional_context = self.entangled_traits[trait]
                memory = conditional_context.get_fused_memory(is_entangled)
            else:
                memory = self._get_fused_memory_without_entanglement(trait)
            trait_dict[trait] = memory
        return Personality(trait_dict)



@dataclass
class ConditionalMemory():
    """
    This is a wrapper for a Memory object.

    Specifically, this represents a memory defined outside of a conditional context, that may have
    been modified inside the conditional context. The branch_id of the conditional context
    is used to identify the entanglement (if any).
    """
    memory: Memory | None
    branch_id: uuid.UUID

    def get_dependency_depths_set(self) -> set[int]:
        """
        Return a set of the depths of all impressions of this memory
        """
        if self.memory is None: return None
        return set([i.shadow.entity.depth for i in self.memory.impressions])

    def get_memory(self, is_entangled: bool):
        """
        Return the underlying memory, with its conditional branch as its entanglement the memory
        [is_entangled]
        """
        if self.memory is None: return None
        if is_entangled: return self.memory.with_entanglement(Entanglement(self.branch_id))
        else: return self.memory

    # TODO: smoothen out this logic
    def get_function_set(self) -> set:
        """
        Return the set of all functions of this memory.
        """
        if self.memory is None: return None
        return set([instance for i in self.memory.impressions for instance in i.shadow.function_instances])

@dataclass
class ConditionalContext(AbstractConditionalContext):
    """
    This represents a slice accross conditonal branches of all conditional memories for a single,
    named variable. For instance, if 'x' is defined before a conditonal statement, and modified in
    each of the three branches, then a ConditionalContext for 'x' would contain three
    ConditionalMemories, one for it's memory in each branch.
    """
    memory_name: str
    conditional_memories: list[ConditionalMemory]

    def check_for_entanglement(self) -> bool:
        """
        Returns true if this variable may contain an entanglement. A conditional context always has
        at least two conditional memories. (if/else; if/default).

        Possible entanglement is defined as having different depths across different branchs of
        the conditional.
        """
        if self._possible_entanglement is not None: return self._possible_entanglement

        # case for impressions.
        # entanglement occurs if there is is non-homogeneity.
        depth_sets = [memory.get_dependency_depths_set() for memory in self.conditional_memories]
        impressions_entangled = not all(sets == depth_sets[0] for sets in depth_sets if sets is not None)

        # case for functions
        function_sets = [memory.get_function_set() for memory in self.conditional_memories]
        functions_entangled = not all(sets == function_sets[0] for sets in function_sets if sets is not None)

        self._possible_entanglement = impressions_entangled or functions_entangled
        # print(self.memory_name, self.has_possible_entanglement)
        return self._possible_entanglement

    def get_fused_memory(self, is_entangled: bool) -> list[Memory]:
        """
        Return the fused memory across all branches of this conditional.
        """
        memories = [cm.get_memory(is_entangled) for cm in self.conditional_memories]
        return Memory.merge_all([m for m in memories if m is not None], rewrites=True)

@dataclass
class FusionContext(AbstractConditionalContext):
    """
    Represents the entire context after a conditional, including ConditionalContexts for all
    modified memories.
    """
    conditional_contexts: list[ConditionalContext]
    shadow_contexts: list[ShadowContext]

    def get_contexts(self) -> list[ShadowContext | ConditionalContext]:
        """
        Return a list of all contexts that could exhibit entanglement.
        """
        return self.conditional_contexts + self.shadow_contexts

    def has_entanglement(self):
        """
        Per the isolation principle, a context after a conditional may be entangled if there are
        at least two conditional contexts (variables) which exhibit possible entanglement.
        """
        if self._possible_entanglement is not None: return self._possible_entanglement
        possible_entanglements = [context.check_for_entanglement() for context in self.get_contexts()]
        self._possible_entanglement = possible_entanglements.count(True) > 1
        return self._possible_entanglement

    def fuse_memories(self) -> list[Memory]:
        return [conditional_context.get_fused_memory(is_entangled=self.has_entanglement())
                for conditional_context in self.conditional_contexts]

    def fuse_personalities(self) -> list[Personality]:
        return [shadow_context.get_fused_personality(is_entangled=self.has_entanglement())
                for shadow_context in self.shadow_contexts]

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
        self.reality_ids = [uuid.uuid4() for _ in range(self.number_of_realities())]

    def number_of_realities(self) -> int:
        """
        :return: The number of realties (branches) of a conditional, including the default reality
        :rtype: int
        """
        return len(self.branch_states) + (0 if self.branching_is_exhaustive() else 1)

    def set_up_fusion_context(self, names: list[str], shadow_uids: list[uuid.UUID]) -> FusionContext:
        fusion_context = FusionContext([], [])

        # init the fusion context
        for name in names:
            prior_memory = self.origin_state.get_memory(name)

            # update set contains the individual memories from each branch reality
            update_set = [self.get_memory_in_branch(branch, name, prior_memory)
                          for branch in self.branch_states]
            if not self.branching_is_exhaustive():
                update_set.append(prior_memory)
            conditional_memories = [ConditionalMemory(memory, id) for memory, id in zip(update_set, self.reality_ids)]
            fusion_context.conditional_contexts.append(ConditionalContext(name, conditional_memories))

        for uid in shadow_uids:
            prior_shadow = self.origin_state.get_shadow(uid)

            update_set = [self.get_shadow_in_branch(branch, uid, prior_shadow)
                          for branch in self.branch_states]
            if not self.branching_is_exhaustive():
                update_set.append(prior_shadow)
            shadow_context = ShadowContext(prior_shadow.entity, update_set, self.reality_ids)
            fusion_context.shadow_contexts.append(shadow_context)

        return fusion_context

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
        return memory if memory is not None else prior_memory

    def get_shadow_in_branch(self, branch: State, uid: uuid.UUID, prior_shadow: Shadow) -> Shadow | None:
        # TODO: this logic may not be accurate
        # if a branch has a return statement, then there is no memory at the end of the branch,
        # provided that prior_shadow is not of a return/argument value
        if RealityFuser.branch_has_return_statement(branch) and prior_shadow and prior_shadow.entity.depth > 0:
            return None

        shadow = branch.get_shadow(uid)
        return shadow if shadow is not None else prior_shadow

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

    def all_updated_shadows_ids(self) -> set[uuid.UUID]:
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

    @staticmethod
    def _fuse_together(shadows_or_memories_from_different_realities: list[Shadow] | list[Memory]):
        match shadows_or_memories_from_different_realities[0]:
            case Shadow(): return Shadow.merge_all(shadows_or_memories_from_different_realities)
            case Memory(): return Memory.merge_all(shadows_or_memories_from_different_realities,
                                                   rewrites=True)

    @staticmethod
    def _collect_paralleled_shadows_or_memories_from_different_outcomes(pos: int, outcomes: list[list[Shadow | Memory]]) -> list[Shadow] | list[Memory]:
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
        return [RealityFuser._fuse_together(
            RealityFuser._collect_paralleled_shadows_or_memories_from_different_outcomes(pos, outcomes))
            for pos in parallels]

    def fuse_realities_after_conditional(self):
        """
        Apply all necessary fusing after a branching conditional to bring all
        types back to a single value for the main timeline to proceed.
        """
        updated_memories_names = self.all_updated_memory_names()
        updated_shadow_uids = self.all_updated_shadows_ids()
        fusion_context = self.set_up_fusion_context(updated_memories_names, updated_shadow_uids)

        memories = fusion_context.fuse_memories()
        for name, memory in zip(updated_memories_names, memories):
            self.origin_state.add_memory(name, memory)

        personalities = fusion_context.fuse_personalities()
        for uid, personality in zip(updated_shadow_uids, personalities):
            self.origin_state.update_personality(uid, personality)

    def branching_is_exhaustive(self) -> bool:
        """
        :return: True if the branching is exhaustive
        :rtype: bool
        """
        if self.origin_state.get_all_children()[-1].type == "seq":
            return True
        return False

    # TODO: hashing likely is circular
    def compute_hash(self, objs: set[Shadow | Memory]) -> int:
        hashstr = ""
        for obj in objs:
            hashstr += str(hash(obj))
        return hash(hashstr)

    def get_hash_of_current_state(self) -> int:
        things: set[Memory | Shadow] = set()
        for name in self.all_updated_memory_names():
            for branch_state in self.branch_states:
                things.add(branch_state.get_memory(name))

        for uid in self.all_updated_shadows_ids():
            for branch_state in self.branch_states:
                things.add(branch_state.get_shadow(uid))
        return self.compute_hash(things)
