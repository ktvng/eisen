from __future__ import annotations
import uuid

from alpaca.utils import Visitor
from alpaca.concepts import Type

import eisen.adapters as adapters
from eisen.common.eiseninstance import FunctionInstance

from eisen.state.memoryvisitorstate import MemoryVisitorState
from eisen.trace.entity import Angel
from eisen.trace.memory import Memory, Impression
from eisen.trace.shadow import Shadow
from eisen.trace.entity import origin_entity
from eisen.trace.delta import FunctionDelta
from eisen.trace.entanglement import Entanglement
from eisen.trace.functionargs import FunctionsAsArgumentsLogic

State = MemoryVisitorState
class CallHandler:
    def __init__(self,
                 impression: Impression,
                 node: adapters.Call,
                 delta: FunctionDelta,
                 param_memories: list[Memory]) -> None:
        """
        Create a new CallHandler

        :param impression: The impression of with entanglement/function information.
        :param node: The AST node of the function
        :param delta: The delta caused by the function
        :param param_memories: An list of memories, corresponding to, and in the same order, as the
        parameters passed into the eisen function call.
        """
        # print("call handling for", delta.function_name)
        self.impression = impression
        self.node = node
        self.state: MemoryVisitorState = node.state
        self.delta = delta
        self.index: dict[uuid.UUID, Memory] = {}
        self.param_memories: list[Memory] = param_memories

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

            # if the shadow is of a pure function, then the entity is the origin_entity. As pure
            # functions do not need to be modified, we can skip here.
            # TODO: can we structure the algorithm so we don't need this?
            if i.shadow.entity == origin_entity: continue

            shadow = self.state.get_shadow(i.shadow.entity)
            m = shadow.personality.get_memory(i.root.join(angel.trait))

            # If the memory at that trait does not exist, we need to create a new Angel, as this
            # means that even in this context, 'a.b' does not exist.
            if m is None:
                m = self.state.create_new_angel_memory(i.root.join(angel.trait), shadow.entity)
                self.state.add_trait(shadow, trait=i.root.join(angel.trait), memory=m)
            memories.append(m)
        return memories

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
            self.index[angel.uid] = self.resolve_angel_into_memories(angel)

    def resolve_angels(self):
        """
        Resolve any changes to angels inside of the function call to the corresponding changes
        to real entities in the parent of that function call.
        """
        # Remapping is necessary so that any dependency uids stored in the Shadow within the
        # delta of f now refer to the uids of parameters which were passed into f.
        angel_shadow_dict = { s.entity.uid: s.remap_via_index(self.index)
                                for s in self.delta.angel_shadows.values() }
        for angel in self.delta.angels:
            # The Angel carries any dependencies that were added within f. We need to update the
            # entities which the Angel could 'guard' that exists outside of f.
            #
            # First we determine the possible Memories which could be associated to the angel
            for m in self.resolve_angel_into_memories(angel):
                # For each impression of that Memory, we can identify the entity that the Angel
                # could refer to. Having the impression allows us to modify the latest shadow
                # of that entity with the shadow of the Angel, noting that we use the remapped
                # shadow.
                for impression in m.impressions:
                    self.state.update_source_of_impression(
                        impression,
                        with_shadow=angel_shadow_dict.get(angel.uid))


    def resolve_updated_parameters(self, param_memories: list[Memory]):
        """
        Resolve any changes to the parameters of the function call which to the corresponding
        changes to the real entities that were supplied as paramters in the parent of that function
        call.
        """
        arg_shadows = [s.remap_via_index(self.index) for s in self.delta.arg_shadows]
        for memory, update_with_shadow in zip(param_memories, arg_shadows):
            for impression in memory.impressions:
                # if the shadow is of a pure function, then the entity is the origin_entity. As pure
                # functions do not need to be modified, we can skip here.
                # TODO: can we structure the algorithm so we don't need this?
                if impression.shadow.entity == origin_entity: continue
                self.state.update_source_of_impression(impression, update_with_shadow)

    @staticmethod
    def should_select_shadow(type: Type) -> bool:
        """
        Return true if, based on the [type], we should return the shadow instead of a memory. This
        is the case for creating new objects (as the object is created as a real entity inside the
        parent function), and in the case of primitives, which do not have memories.

        In short, this should return true if we are returning a "true object" and not a pointer/
        memory of one.
        """
        return type.restriction.is_new_let() or type.restriction.is_primitive()

    @staticmethod
    def _select_shadow_or_memory(
            i: int,
            type: Type,
            shadows: list[Shadow],
            memories: list[Memory]) -> Shadow | Memory:
        """
        For the [i]th return value and its [type], return either the shadow or memory that
        corresponds to it.
        """
        match CallHandler.should_select_shadow(type):
            case True: return shadows[i]
            case False: return memories[i]

    def _filter_return_values(self, shadows: list[Shadow], memories: list[Memory]) -> list[Shadow | Memory]:
        """
        Return an ordered list of return values of this function, where each value is either a
        Shadow or a Memory depending on the eisen type of that return value.
        """
        return_types = self.node.get_function_return_type().unpack_into_parts()
        return [CallHandler._select_shadow_or_memory(i, type, shadows, memories)
            for i, type in enumerate(return_types)]

    def _add_entanglement(self, memory: Memory) -> Memory:
        """
        If the current function call occurs in the context of an function that is entangled,
        then the resulting return value must also have this entanglement.
        """
        if self.impression is not None and self.impression.entanglement is not None:
            return memory.with_entanglement(self.impression.entanglement)
        return memory

    def resolve_updated_returns(self) -> list[Shadow | Memory]:
        """
        Resolve the correct return values for this function.
        """
        if self.node.get_function_return_type() == self.state.get_void_type():
            return []

        # TODO: should shadows also get entanglements? Probably not as conditional initialization
        # should not be supported

        # We need to remap all shadows/memories in the delta so that they correctly refer to the
        # real entities in the parent of this function call.
        return self._filter_return_values(
            shadows=[s.remap_via_index(self.index) for s in self.delta.ret_shadows],
            memories=[self._add_entanglement(m.remap_via_index(self.index))
                      for m in self.delta.ret_memories])

    def resolve_entity_moves(self, param_memories: list[Memory]):
        """
        Resole any parameters which may be moved into the child function call.
        """
        for type_, memory in zip(self.node.get_function_argument_type().unpack_into_parts(), param_memories):
            if type_.restriction.is_move():
                for impression in memory.impressions:
                    impression.shadow.entity.moved = True

    def resolve_outcome(self) -> list[Shadow | Memory]:
        """
        Perform all resolutions and return a list of return values from the child function call.
        """
        if self.node.is_print():
            return self

        self.build_remapping_index(self.param_memories)
        self.resolve_angels()
        self.resolve_updated_parameters(self.param_memories)
        self.resolve_entity_moves(self.param_memories)
        return self.resolve_updated_returns()

class CallHandlerFactory:
    """
    Create the list of CallHandlers required to process a function call, being aware of separate
    realities due to entanglements.
    """

    @staticmethod
    def get_call_handlers(
            node: adapters.Call,
            fn: Visitor,
            param_memories: list[Memory]) -> list[CallHandler]:
        """
        Return a list of CallHandlers to process a function call, where each CallHandler processes
        the inputs for a single entanglement. [param_memories] should be the memories possible for
        each parameter to the function call, ordered in the same way such that the nth element in
        this list is the nth parameters supplied to the function.
        """
        indeterminate_function_parameters = FunctionsAsArgumentsLogic.get_memories_of_parameters_that_are_functions(node, param_memories)
        handlers = []
        for impression, delta in CallHandlerFactory._aquire_function_deltas(node, fn, indeterminate_function_parameters):
            handlers.extend(CallHandlerFactory._get_call_handlers_for_each_reality(
                variable_caller=impression,
                node=node,
                delta=delta,
                param_memories=FunctionsAsArgumentsLogic.get_full_parameter_memories_including_currying(
                                                            caller=impression,
                                                            parameters=param_memories)))
        return handlers

    @staticmethod
    def _associate_function_instance_to_delta(
            node: adapters.Call,
            function_instance: FunctionInstance,
            fn: Visitor,
            function_parameters: list[Shadow] = None
            ):
        """
        Obtain the function delta for a given [function_instance]
        """
        delta = fn.function_db.get_function_delta(function_instance.get_full_name())
        if delta is None:
            delta = FunctionDelta.compute_for(adapters.Def(node.state.but_with(
                ast=function_instance.ast,
                function_parameters=function_parameters)), fn)
            # delta = fn.function_db.get_function_delta(function_instance.get_full_name())
        return delta

    @staticmethod
    def _get_impression_delta_pairs(
            node: adapters.Call,
            impression: Impression | None,
            function_instance: FunctionInstance,
            fn: Visitor,
            function_parameters: list[Shadow]) -> tuple[Impression | None, FunctionDelta]:

        return (impression, CallHandlerFactory._associate_function_instance_to_delta(
                    node=node,
                    function_instance=function_instance,
                    fn=fn,
                    function_parameters=function_parameters))

    @staticmethod
    def _aquire_function_deltas(node: adapters.Call, fn: Visitor, functions: list[Memory]) -> list[tuple[Impression | None, FunctionDelta]]:
        """
        Returns tuples of Impression? and FunctionDelta, where impression is the impression of a
        function (if it is called from a variable) and FunctionDelta is the delta which should be applied
        """
        if node.is_pure_function_call():
            combos = FunctionsAsArgumentsLogic.get_all_function_combinations(functions)
            return [CallHandlerFactory._get_impression_delta_pairs(
                impression=None,
                node=node,
                function_instance=node.get_function_instance(),
                fn=fn,
                function_parameters=combo) for combo in combos]
        else:
            # take the first as there should only be one Memory returned from a (ref ...)
            caller_memory: Memory = fn.apply(node.state.but_with_first_child())[0]
            combos = FunctionsAsArgumentsLogic.get_all_function_combinations_for_indeterminate_caller(
                caller=caller_memory,
                function_parameters=functions)
            return [CallHandlerFactory._get_impression_delta_pairs(
                impression=impression,
                node=node,
                function_instance=instance,
                fn=fn,
                function_parameters=combo) for impression, instance, combo in combos]

    @staticmethod
    def _get_call_handlers_for_each_reality(
            variable_caller: Impression,
            node: adapters.Call,
            delta: FunctionDelta,
            param_memories: list[Memory]) -> list[CallHandler]:
        """
        Return a list of CallHandlers where each handler exclusively processes the call for a given
        entanglement.
        """
        # if the function is entangled, only consider that entanglement
        if variable_caller and variable_caller.entanglement:
            return [CallHandler(
                variable_caller, node, delta,
                [memory.for_entanglement(variable_caller.entanglement) for memory in param_memories])]

        # otherwise, divide the parameters by general entanglement
        realities = CallHandlerFactory._divide_parameters_by_entanglement(param_memories)

        # if there are no entanglements, then simply return a call handler with the entire
        # param_memories
        if not realities: return [CallHandler(variable_caller, node, delta, param_memories)]

        # finally return a call handler for each entanglement
        return [CallHandler(variable_caller, node, delta, reality) for reality in realities]

    @staticmethod
    def _find_next_entanglement_present(param_memories: list[Memory]) -> Entanglement:
        """
        Iterates through all memories nad their entanglements to find a the next entanglement
        present in the set and returns it.
        """
        for memory in param_memories:
            for impression in memory.impressions:
                if impression.entanglement:
                    return impression.entanglement
        return None

    @staticmethod
    def _divide_parameters_by_entanglement(param_memories: list[Memory]) -> list[list[Memory]]:
        """
        Provided an ordered list of memories in the same order as the parameters to this function
        call, [param_memories], splits this list into multiple lists of memories, preserving the
        order, but ensuring that each list only contains a single entanglement.
        """
        realities: list[list[Memory]] = []
        while entanglement := CallHandlerFactory._find_next_entanglement_present(param_memories):
            entangled_memories = [memory.for_entanglement(entanglement) for memory in param_memories]
            realities.append(entangled_memories)
            param_memories = [memory.not_for_entanglement(entanglement) for memory in param_memories]
        return realities
