from __future__ import annotations
import uuid
import itertools

from alpaca.utils import Visitor
from alpaca.concepts import Type

import eisen.adapters as adapters
from eisen.common.eiseninstance import EisenFunctionInstance

from eisen.state.memoryvisitorstate import MemoryVisitorState
from eisen.trace.entity import Angel
from eisen.trace.memory import Memory
from eisen.trace.shadow import Shadow
from eisen.trace.delta import FunctionDelta
from eisen.trace.branchedrealitytag import BranchedRealityTag

State = MemoryVisitorState
class CallHander:
    def __init__(self,
                 node: adapters.Call,
                 delta: FunctionDelta,
                 param_memories: list[Memory],
                 tags: set[BranchedRealityTag],
                 all_reality_tags: set[BranchedRealityTag]) -> None:

        print("CALL HANDLER", delta.function_name)
        for t in tags:
            print("calling with tags", t)
        self.node = node
        self.state: MemoryVisitorState = node.state
        self.delta = delta
        self.index: dict[uuid.UUID, Memory] = {}
        self.param_memories: list[Memory] = [m.for_the_given_realities(tags, all_reality_tags) for m in param_memories]
        self.tags = tags
        self.all_reality_tags = all_reality_tags

    def resolve_angel_into_memories(self, angel: Angel) -> list[Memory]:
        """
        Let f(a: A) be a function. The variable 'a' may have some attribute 'a.b' which is
        variable dependency to some type B. In this case, 'a' would not own the memory of 'b',
        but only own a reference to some external 'b'.

        Within the function f, 'a.b' would not be resolvable, as it must refer to a different
        entity 'b' that is unavailable in the scope of f. Therefore, we use an Angel as a type
        of entity which is not available in the current scope.

        As 'a.b' is a variable, it would be represented as a Memory. Therefore we must resolve some
        [angel] into the Memory it refers to.

        When 'a' is an entity itself, there is uniquely one Memory that is associated to the Angel.
        However, if 'a' is a variable, and could refer to many actual entities, then each
        entity 'a' could have an impression of may provide a Memory to associate with the [angel].

        Therefore we must return a list of Memories.
        """
        # This is the memory of all possible entities to which the angel could guard.
        original_memory = self.index.get(angel.entity.uid)

        memories = []
        for i in original_memory.impressions:
            # For a given impression, we get current shadow of the entity, and obtain, for this
            # shadow, the memory of the Angel's trait.
            shadow = self.state.get_shadow(i.shadow.entity)
            m = shadow.personality.get_memory(i.root.join(angel.trait))

            # If the memory at that trait does not exist, we need to create a new Angel, as this
            # means that even in this context, 'a.b' does not exist.
            if m is None:
                m = self.state.create_new_angel_memory(i.root.join(angel.trait), shadow.entity)
                self.state.add_trait(shadow, trait=i.root.join(angel.trait), memory=m)
            memories.append(m)
        return memories

    @staticmethod
    def associate_function_instance_to_delta(node: adapters.Call, function_instance: EisenFunctionInstance, fn: Visitor):
        delta = fn.function_db.get_function_delta(function_instance.get_full_name())
        if delta is None:
            fn.apply(node.state.but_with(ast=node.get_ast_defining_the_function()))
            delta = fn.function_db.get_function_delta(function_instance.get_full_name())
        return delta

    @staticmethod
    def aquire_function_deltas_and_tags(node: adapters.Call, fn: Visitor) -> list[FunctionDelta]:
        if node.is_pure_function_call():
            return [(CallHander.associate_function_instance_to_delta(
                node=node,
                function_instance=node.get_function_instance(),
                fn=fn), set([BranchedRealityTag(uuid.UUID(int=0), 0)]), set())]
        else:
            # take the first as there should only be one Memory returned from a (ref ...) node
            caller_memory: Memory = fn.apply(node.state.but_with_first_child())[0]
            all_realities = set()
            for f in caller_memory.functions:
                for tag in f.tags:
                    all_realities.add(tag)
            x = [(CallHander.associate_function_instance_to_delta(
                node=node,
                function_instance=f.function_instance,
                fn=fn), f.tags, all_realities) for f in caller_memory.functions]
            x = []
            for f in caller_memory.functions:
                for t in f.tags:
                    x.append((CallHander.associate_function_instance_to_delta(
                        node=node,
                        function_instance=f.function_instance, fn=fn), set([t]), all_realities))
            return x

    def build_remapping_index(self, param_memories: list[Memory]):
        """
        This generates an index between entities used internal to f, and the actual memories
        which are passed into f.

        :param param_memories: The memories of parameters actually passed to f.
        :type param_memories: list[Memory]
        """
        # The uid of an argument entity created for the delta is mapped to the actual
        # parameter passed to f in this instance.
        arg_uids = [s.entity.uid for s in self.delta.arg_shadows]
        for uid, memory in zip(arg_uids, param_memories):
            self.index[uid] = memory

        # Likewise, each Angel uid is mapped to the list of Memories which it could
        # refer to.
        for angel in self.delta.angels:
            possible_argument_trait_memories = self.resolve_angel_into_memories(angel)
            self.index[angel.uid] = possible_argument_trait_memories


    def resolve_angels(self):
        # Remapping is necessary so that any dependency uids stored in the Shadow within the
        # delta of f now refer to the uids of parameters which were passed into f.
        angel_shadow_dict = { s.entity.uid: s.remap_via_index(self.index)
                                for s in self.delta.angel_shadows.values() }
        for angel in self.delta.angels:
            possible_argument_trait_memories = self.resolve_angel_into_memories(angel)

            # The Angel carries any dependencies that were added within f. We need to update the
            # entities which the Angel could 'guard' that exists outside of f.
            #
            # First we determine the possible Memories which could be associated to the angel
            for m in possible_argument_trait_memories:
                # For each impression of that Memory, we can identify the entity that the Angel
                # could refer to. Having the impression allows us to modify the latest shadow
                # of that entity with the shadow of the Angel, noting that we use the remapped
                # shadow.
                for impression in m.impressions:
                    self.state.update_source_of_impression(
                        impression,
                        with_shadow=angel_shadow_dict.get(angel.uid))


    def resolve_updated_arguments(self, param_memories: list[Memory]):
        arg_shadows = [s.remap_via_index(self.index) for s in self.delta.arg_shadows]
        for memory, update_with_shadow in zip(param_memories, arg_shadows):
            for impression in memory.for_the_given_realities(self.tags, self.all_reality_tags).impressions:
                self.state.update_source_of_impression(impression,
                    update_with_shadow.for_the_given_realities(impression.tags, self.all_reality_tags))

    @staticmethod
    def should_select_shadow(type: Type):
        return type.restriction.is_new_let() or type.restriction.is_primitive()

    def select_shadow_or_memory(self, i: int, type: Type, shadows: list[Shadow], memories: list[Memory]) -> Shadow | Memory:
        match CallHander.should_select_shadow(type):
            case True: return shadows[i].for_the_given_realities(self.tags, self.all_reality_tags)
            case False:
                print("original memory: ", memories[i])
                memory = memories[i].for_the_given_realities(self.tags, self.all_reality_tags).with_tag(next(iter(self.tags))) #.replace_base_with_tag(next(iter(self.tags)))
                return memory


    def filter_return_values(self, shadows: list[Shadow], memories: list[Memory]):
        return_types = self.node.get_function_return_type().unpack_into_parts()
        return [self.select_shadow_or_memory(i, type, shadows, memories)
            for i, type in enumerate(return_types)]

    def resolve_updated_returns(self) -> list[Shadow | Memory]:
        if self.node.get_function_return_type() == self.state.get_void_type():
            return []

        return self.filter_return_values(
            shadows=[s.remap_via_index(self.index) for s in self.delta.ret_shadows],
            memories=[m.remap_via_index(self.index) for m in self.delta.ret_memories])

    def resolve_entity_moves(self, param_memories: list[Memory]):
        for type_, memory in zip(self.node.get_function_argument_type().unpack_into_parts(), param_memories):
            if type_.restriction.is_move():
                for impression in memory.impressions:
                    impression.shadow.entity.moved = True

    def start(self) -> CallHander:
        if self.node.is_print():
            return self

        self.build_remapping_index(self.param_memories)
        return self

    def resolve_outcome(self) -> list[Shadow | Memory]:
        self.resolve_angels()
        self.resolve_updated_arguments(self.param_memories)
        self.resolve_entity_moves(self.param_memories)
        ret = self.resolve_updated_returns()
        for r in ret:
            print(f"{self.delta.function_name} returning   ", r)
        return ret
