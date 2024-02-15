from __future__ import annotations
import itertools
from enum import Enum

from alpaca.concepts import Type

from eisen.common.eiseninstance import FunctionInstance
from eisen.common.traits import TraitImplementation, TraitsLogic
from eisen.trace.memory import Memory, Impression
from eisen.trace.shadow import Shadow, Personality
from eisen.trace.entity import Entity, Trait
import eisen.adapters as adapters
from eisen.state.memoryvisitorstate import MemoryVisitorState

State = MemoryVisitorState

class CurryingLogic:
    ...

class Blessing:
    """
    When performing the memory checking, there are some functions which cannot be processed until
    certain conditions are known. Three such cases are known:

        1. The function takes a function as an argument
                e.g. fn someFunc(f: (mut obj) -> obj, o: obj) {...}

        2. The function takes a trait as an argument
                e.g. fn someFunc(t: myTrait) {...}

        3. The function takes a struct which could have a function as an attribute.
                e.g. fn someFunc(s: myStruct) {
                         s.attribute_function()
                     }

    As the identity of 'f', 't', or 's.attribute_function' may change what shadows get changed or
    what impressions are formed after they are run, it is insufficient from the type information
    to know how these functions behave at a memory level.

    Thus, when processing functions which satisfy these three cases, we must hold off until the
    instance identity is known, where instance identity is in each case:
        1. The actual function assigned to f
        2. The actual struct type which implements t
        3. The actual function assigned as s.attribute_function

    Collectively, this information is referred to as a Blessing (as it is a thing imparted from
    an external context that imbues f/t/s with special behavior and distinct status.)


    """
    class Type(Enum):
        NoBlessing = 0
        FunctionArgument = 1
        TraitArgument = 2
        StructWithFunctionAttribute = 3

    def __init__(self,
                 blessing_type: Blessing.Type,
                 trait_implementer: Type | None = None,
                 function_shadow: Shadow | None = None,
                 struct_shadow: Shadow | None = None
                 ) -> None:
        self.type = blessing_type
        self.trait_implementer_type = trait_implementer
        self.function_shadow = function_shadow
        self.struct_shadow = struct_shadow


    def bless_representative_in_method(self, state: State, representative: Shadow) -> None:
        """
        Bestow the [representative] (parameter name) inside the method with the provided
        [blessing] depending on its Blessing.Type


        """
        match self.type:
            case Blessing.Type.NoBlessing: return
            case Blessing.Type.FunctionArgument:
                representative.function_instances.append(self.function_shadow.function_instances[0])
                function_parameter = self.function_shadow
                curried_args = function_parameter.personality.size()

                # for each curried argument, use an angel to guard the memory of that curried arg, as it
                # isn't available in this scope.
                traits = [Trait(str(i)) for i in range(curried_args)]
                personality = Personality({ trait: state.create_new_angel_memory(
                                                        trait=trait,
                                                        entity=representative.entity)
                                            for trait in traits })
                state.update_personality(representative.entity, personality)
                state.update_memory_to_latest(representative.entity.name)

            case Blessing.Type.TraitArgument:
                representative.entity.type = self.trait_implementer_type
            case Blessing.Type.StructWithFunctionAttribute:
                # TODO: implement
                return

    @staticmethod
    def is_struct_with_function_attribute(struct_type: Type):
        # TODO: allow for multi-depth handling
        return False


    @staticmethod
    def are_blessings_required(function_type: Type) -> bool:
        """
        True if the function of [function_type] requires blessings to be processed
        """
        return not all(Blessing.get_required_blessing_type(t) == Blessing.Type.NoBlessing
            for t in function_type.get_argument_type().unpack_into_parts())

    @staticmethod
    def get_required_blessing_type(type_: Type) -> Blessing.Type:
        if type_.is_function(): return Blessing.Type.FunctionArgument
        if type_.is_trait(): return Blessing.Type.TraitArgument
        if Blessing.is_struct_with_function_attribute(type_): return Blessing.Type.StructWithFunctionAttribute
        return Blessing.Type.NoBlessing

    @staticmethod
    def get_blessings_for_parameter(param_type: Type, memory: Memory) -> list[Blessing]:
        if len(memory.impressions) == 0:
            return [Blessing(Blessing.Type.NoBlessing)]

        match blessing_type := Blessing.get_required_blessing_type(param_type):
            case Blessing.Type.NoBlessing:
                return [Blessing(blessing_type)]
            case Blessing.Type.FunctionArgument:
                # TODO: can function_instance be just one function instance?
                return [Blessing(blessing_type, function_shadow=i.shadow)
                        for i in memory.impressions]
            case Blessing.Type.TraitArgument:
                return [Blessing(blessing_type, trait_implementer=i.shadow.entity.type)
                        for i in memory.impressions]
            case Blessing.Type.StructWithFunctionAttribute:
                # TODO: implement
                return [Blessing(Blessing.Type.NoBlessing)]

    @staticmethod
    def get_all_combinations_of_blessings(
            function_argument_type: Type,
            function_params: list[Memory]) -> list[list[Blessing]]:
        """
        Multiple blessings may be possible if for a given parameter, a value is passed into that
        parameter which may be associated with multiple actual things (e.g. a function reference could
        be assigned to multiple different actual functions)

        If this is the case, the MemoryVisitor will need check all possible combinations of these
        actual objects, hence all possible combinations of blessings.
        """
        blessings_for_parameter = [Blessing.get_blessings_for_parameter(param_type, memory)
                                   for param_type, memory in zip(function_argument_type.unpack_into_parts(), function_params)]

        # Each parameter has a set of associated blessings. Return all possible configurations of
        # blessings taking one from each parameter.
        return list(itertools.product(*blessings_for_parameter))

class FunctionsAsArgumentsLogic:
    """
    This class encapsulates the logic required to correctly handle passing in
    functions as arguments. The logic should be kept here to keep it cohesive and
    in one place, given that multiple parts of the algorithm must be touched.
    """

    @staticmethod
    def get_memories_of_parameters_that_are_functions(node: adapters.Call, params: list[Memory]) -> list[Memory]:
        """
        Return an ordered list of Memories for each argument of a method that is a function
        """
        component_wise_argument_types = node.get_function_argument_type().unpack_into_parts()
        return [param for type_, param in zip(component_wise_argument_types, params)
                if type_.is_function() or type_.is_trait()]

    @staticmethod
    def get_all_function_combinations(function_parameters: list[Memory]) -> list[list[Shadow]]:
        """
        For the provided ordered list of function memories, each memory may refer to more than one
        actual function (i.e. if that memory were assigned over a conditional block). But in order
        to correctly run the memory tracer, we need a definite function. Therefore, this method returns
        all possible combinations of individual functions.

        For N parameters that are functions, given that each memory as M possible functions, there
        will be M^N combinations.
        """
        if not function_parameters: return [None]
        return list(itertools.product(*[memory.impressions.get_shadows()
                                        for memory in function_parameters]))

    @staticmethod
    def _get_function_instance_from_caller_impression(state: State,
                                           impression: Impression,
                                           caller_type: Type,
                                           called_function_name: str,
                                           called_function_argument_type: Type):
        if caller_type is not None and caller_type.is_trait():
            # if it's a trait, we return the trait implementation
            implementation_type = impression.shadow.entity.type
            impl: TraitImplementation = state.get_enclosing_module().get_obj("trait_implementations", TraitImplementation.get_key(caller_type, impression.shadow.entity.type))
            # print("impl:", caller_type, impression.shadow.entity.type)
            type_to_look_for = TraitsLogic._replace_Self_type_with_implementation_type(called_function_argument_type, implementation_type)
            found_instances = [i for i in impl.implementations if i.name_of_trait_attribute == called_function_name and i.type.get_argument_type() == type_to_look_for]
            if len(found_instances) != 1:
                raise Exception(f"Found instances should be one {found_instances}")
            found_instance = found_instances[0]
            return found_instance
        else:
            # if it's a function reference, we return the reference.
            if len(impression.shadow.function_instances) != 1:
                print(impression)
                raise Exception("A shadow should only have one function_instance.")
            return impression.shadow.function_instances[0]

    @staticmethod
    def get_full_parameter_memories_including_currying(
            caller: Impression | None,
            parameters: list[Memory]) -> list[Memory]:
        """
        _summary_

        :param impression: The impression of the caller, which would reference the shadow that records
                           curried parameters.
        :param parameters: The supplied parameters to the function call.
        :return: A list of parameters, now including all arguments, including those curried prior.
        """
        curried_params = caller.shadow.personality.as_curried_params() if caller else []
        return curried_params + parameters

    @staticmethod
    def cannot_process_method_yet(node: adapters.Def, state: MemoryVisitorState) -> bool:
        """
        We cannot process a method definition if that methods takes in functional parameters,
        but we haven't reached a point in the code where the method is called with the definite
        function instance. This is because we don't know what that function could to.
        """
        case1 = node.has_function_as_argument() and state.get_function_parameters() is None
        case2 = node.has_trait_as_argument() and state.get_function_parameters() is None
        return case1 or case2

    @staticmethod
    def update_shadow_to_be_like_function_parameter(
            state: MemoryVisitorState,
            function_parameter: Shadow,
            representative_in_method: Entity):
        """
        For a function parameter, there will be some [representative_in_method] which is an entity
        that is in the argument of the function. This representative needs to be updated to be akin
        to the [function_parameter], such that is has the same curried arguments and the same
        function instances.

        Because the curried parameters do not exist inside the method, they must be guarded by
        angels.
        """
        if representative_in_method.type.is_trait():
            representative_in_method.type = function_parameter.entity.type
            return

        shadow = state.get_shadow(representative_in_method)
        shadow.function_instances.extend(function_parameter.function_instances)
        curried_args = function_parameter.personality.size()

        # for each curried argument, use an angel to guard the memory of that curried arg, as it
        # isn't available in this scope.
        traits = [Trait(str(i)) for i in range(curried_args)]
        personality = Personality({ trait: state.create_new_angel_memory(
                                                trait=trait,
                                                entity=representative_in_method)
                                    for trait in traits })
        state.update_personality(representative_in_method, personality)
        state.update_memory_to_latest(representative_in_method.name)
