from __future__ import annotations
import dataclasses
from dataclasses import dataclass
from typing import Callable
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
from eisen.trace.functionargs import FunctionsAsArgumentsLogic, Blessing
from eisen.common.binding import Binding

State = MemoryVisitorState
class CallHandler:
    def __init__(self, s: Situation) -> None:
        """
        Create a new CallHandler

        """
        # print("call handling for", delta.function_name)
        self.impression = s.caller_impression
        self.node = s.call_node
        self.state: MemoryVisitorState = self.node.state
        self.delta = s.delta
        self.index: dict[uuid.UUID, Memory] = {}
        self.param_memories = s.call_parameters

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
    def should_select_shadow(binding: Binding) -> bool:
        """
        Return true if, based on the [type], we should return the shadow instead of a memory. This
        is the case for creating new objects (as the object is created as a real entity inside the
        parent function), and in the case of primitives, which do not have memories.

        In short, this should return true if we are returning a "true object" and not a pointer/
        memory of one.
        """
        return binding == Binding.ret_new or binding == Binding.data


    @staticmethod
    def _select_shadow_or_memory(
            i: int,
            binding: Binding,
            shadows: list[Shadow],
            memories: list[Memory]) -> Shadow | Memory:
        """
        For the [i]th return value and its [type], return either the shadow or memory that
        corresponds to it.
        """
        match CallHandler.should_select_shadow(binding):
            case True: return shadows[i]
            case False: return memories[i]

    def _filter_return_values(self, shadows: list[Shadow], memories: list[Memory]) -> list[Shadow | Memory]:
        """
        Return an ordered list of return values of this function, where each value is either a
        Shadow or a Memory depending on the eisen type of that return value.
        """
        returned_bindings = self.node.get_return_value_bindings()
        return [CallHandler._select_shadow_or_memory(i, binding, shadows, memories)
            for i, binding in enumerate(returned_bindings)]

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
        if self.node.get_function_return_type().equals(self.state.get_void_type(), Type.structural_equivalency):
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
        bindings = self.node.get_argument_bindings()
        for binding, memory in zip(bindings, param_memories):
            if binding == Binding.move:
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

@dataclass
class Situation:
    """
    A representation of the situation surrounding a function call (call ...), with awareness
    of blessings, entanglements, and currying.

    This is necessary because a simple looking call of a function could actual result in multiple
    situations with different tracing and different memory safety. The easiest example is the
    function
        f: (g: (mut obj) -> void, mut o: obj) -> void
    which takes another function 'g' and some object 'o'. The memory safety of 'f' depends in large
    part on the exact identity of 'g'.

    Another common example is passing a trait into a function, where the identity of the struct
    which implements the trait determines the memory safety.

    Therefore a simple call may actually spawn many different situations, and each situations needs
    to be handled differently.
    """

    # The wrapper of the (call ...) AST which encodes all the relevant information
    call_node: adapters.Call = None

    # The impression of the caller
    caller_impression: Impression | None = None

    # The parameters supplied to the call
    call_parameters: list[Memory] | None = None

    # The entanglement (if any) that this call is for
    entanglement: Entanglement | None = None

    # The blessings to provide to the arguments of the function when traced
    blessings: list[Blessing] | None = None

    # The function instance that will be called actually
    function_instance: FunctionInstance = None

    # The delta corresponding to the function instance.
    delta: FunctionDelta = None

class SituationAssessor:
    """
    This is a helper class that adds syntactic sugar when running through a list of situations,
    similar to the chain of responsibility pattern.
    """
    def __init__(self, situation: Situation) -> None:
        self.situations: list[Situation] = [situation]

    def then_perform(self, assessment_fn: Callable[[list[Situation]], list[Situation]], *args) -> SituationAssessor:
        self.situations = assessment_fn(self.situations, *args) if args else assessment_fn(self.situations)
        return self

    def then_return_situations(self) -> list[Situation]:
        return self.situations

class CallHandlerFactory:
    """
    Create a list of CallHandlers to process a function call, with awareness of each situation
    """

    @staticmethod
    def get_call_handlers(
            node: adapters.Call,
            fn: Visitor,
            param_memories: list[Memory]) -> list[CallHandler]:

        # The order of assessments matter here.
        situations = (
            SituationAssessor(Situation(call_node=node))
                .then_perform(CallHandlingLogic.assess_caller, fn)
                .then_perform(CallHandlingLogic.assess_call_parameters, param_memories)
                .then_perform(CallHandlingLogic.assess_function_instance)
                .then_perform(CallHandlingLogic.assess_entanglements)
                .then_perform(CallHandlingLogic.assess_blessings)
                .then_perform(CallHandlingLogic.assess_deltas, fn)
                .then_return_situations())

        return [CallHandler(s) for s in situations]

class CallHandlingLogic:
    @staticmethod
    def assess_caller(current_situations: list[Situation], fn: Visitor) -> list[Situation]:
        """
        Enrich the current situations with awareness of the caller.

        There is no caller for pure function calls. If a function is called from an object attribute
        or from a variable, then there is a caller. After this assessment is run, the caller is known,
        and may intentionally be None.
        """
        new_situations = []
        for situation in current_situations:
            if situation.call_node.is_pure_function_call():
                # Caller impression is still None
                new_situations.append(situation)
            else:
                # take the first as there should only be one Memory returned from a (ref ...)
                caller: Memory = fn.apply(situation.call_node.state.but_with_first_child())[0]
                for impression in caller.impressions:
                    new_situations.append(dataclasses.replace(situation,
                        caller_impression=impression))
        return new_situations

    @staticmethod
    def assess_call_parameters(current_situations: list[Situation], explicit_call_parameters: list[Memory]) -> list[Situation]:
        """
        Enrich the current situations with awareness of the call parameters.

        This takes into account the call parameters passed in explicitly, as well as any curried call
        parameters stored on an object. After this assessment is run the parameters which will be passed
        in are known, and must exist.
        """
        for situation in current_situations:
            if situation.caller_impression is not None:
                situation.call_parameters = FunctionsAsArgumentsLogic.get_full_parameter_memories_including_currying(
                    situation.caller_impression,
                    explicit_call_parameters)
            else:
                situation.call_parameters = explicit_call_parameters
        return current_situations

    @staticmethod
    def assess_function_instance(current_situations: list[Situation]) -> list[Situation]:
        """
        Enrich the current situation with awareness of the function instance which contains the code
        that will be invoked.

        This takes into account curried functions, function variables, and traits, all of which may
        dynamically have different implementations. After this assessment is run, the exact function
        that is invoked is known, and must exist.
        """
        for situation in current_situations:
            if not situation.call_node.is_pure_function_call():
                situation.function_instance = FunctionsAsArgumentsLogic\
                    .get_function_instance_from_caller_impression(
                        situation.call_node.state,
                        situation.caller_impression,
                        situation.call_node)
            else:
                situation.function_instance = situation.call_node.get_function_instance()
        return current_situations

    @staticmethod
    def assess_blessings(current_situations: list[Situation]) -> list[Situation]:
        """
        Enrich the current situation with awareness of the blessings that must be provided to the
        representatives of each parameter from inside the function call.

        This takes into account the fact that there may be multiple blessings for a given parameter,
        and expands to all possible allocations of blessings. After this assessment is run, the
        blessings to bestow are known, and must exist.
        """
        new_situations: list[Situation] = []
        for situation in current_situations:
            function_argument_type = situation.function_instance.type.get_argument_type()
            blessing_allocations = Blessing.get_all_combinations_of_blessings(function_argument_type, situation.call_parameters)
            for allocation in blessing_allocations:
                new_situations.append(dataclasses.replace(situation, blessings=allocation))
        return new_situations

    @staticmethod
    def assess_deltas(current_situations: list[Situation], fn: Visitor) -> list[Situation]:
        """
        Enrich the current situation with the function delta that must be used for trace computation

        This takes into account all preceding enrichments, and must be run at the end or close to
        the list of assessments. After this assessment is run, the exact function delta which ought
        be applied to add/remove memory dependencies is known.
        """
        for situation in current_situations:
            delta = fn.function_db.get_function_delta(situation.function_instance.get_uuid_name())
            if delta is None:
                delta = FunctionDelta.compute_for(adapters.Def(situation.call_node.state.but_with(
                    ast=situation.function_instance.ast,
                    function_parameters=situation.blessings)), fn)
            situation.delta = delta
        return current_situations

    @staticmethod
    def assess_entanglements(current_situations: list[Situation]) -> list[Situation]:
        """
        Enrich the current situation with awareness of the entanglements between the function (if it's
        called from a dynamic caller) as well as entanglements between parameters.

        This takes into account all entanglement information. After this is run, each situation is
        filtered to specifically deal with a single entanglement. If there is no entanglement, the
        situation is unchanged.
        """
        new_situations = []
        for situation in current_situations:
            # If the function is entangled, only consider that entanglement
            if situation.caller_impression and situation.caller_impression.entanglement:
                e = situation.caller_impression.entanglement
                new_situations.append(dataclasses.replace(situation,
                    entanglement=e,
                    call_parameters=[memory.for_entanglement(e) for memory in situation.call_parameters]))
            # otherwise, divide the parameters by general entanglement
            else:
                realities = CallHandlingLogic._divide_parameters_by_entanglement(situation.call_parameters)

                # If no entanglements, return the situation as is
                if not realities: new_situations.append(situation)

                # otherwise, return a new situation for each entanglement
                for reality in realities:
                    new_situations.append(dataclasses.replace(situation,
                        entanglement=reality[0].impressions.first().entanglement,
                        call_parameters=reality))
        return new_situations

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
        while entanglement := CallHandlingLogic._find_next_entanglement_present(param_memories):
            entangled_memories = [memory.for_entanglement(entanglement) for memory in param_memories]
            realities.append(entangled_memories)
            param_memories = [memory.not_for_entanglement(entanglement) for memory in param_memories]
        return realities
