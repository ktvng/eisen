
import itertools

from eisen.common.eiseninstance import FunctionInstance
from eisen.trace.memory import Memory, Impression
from eisen.trace.shadow import Shadow, Personality
from eisen.trace.entity import Entity, Trait
import eisen.adapters as adapters
from eisen.state.memoryvisitorstate import MemoryVisitorState

State = MemoryVisitorState

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
                if type_.is_function()]

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
    def get_all_function_combinations_for_indeterminate_caller(
            caller: Memory,
            function_parameters: list[Memory]) -> list[tuple[Impression, FunctionInstance, list[Shadow]]]:
        """
        If the function being called is not a pure function, but a variable, then this variable may
        itself refer to multiple functions. If that variable would also take in function parameters,
        then we need to consider all combinations of definite caller functions, with all possible
        function parameter combinations

        :param caller: The function that is getting called (may refer to multiple)
        :param function_parameters: The possible function parameters being passed into the caller
        :return: A list of tuples of the impression (for entanglement), the function instance,
                 and the function_parameters
        """
        if any(len(impression.shadow.function_instances) != 1 for impression in caller.impressions):
            # for impression in caller.impressions:
            #     print(impression.shadow.function_instances)
            raise Exception("A shadow should only have one function_instance.")

        return [(impression, impression.shadow.function_instances[0], combo)
            for impression in caller.impressions
                for combo in FunctionsAsArgumentsLogic.get_all_function_combinations(function_parameters)]

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
        return node.has_function_as_argument() and state.get_function_parameters() is None

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
