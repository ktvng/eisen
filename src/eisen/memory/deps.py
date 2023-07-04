from __future__ import annotations
from typing import List, TYPE_CHECKING, Any

from eisen.common.eiseninstance import EisenInstance
if TYPE_CHECKING:
    from eisen.memory.spreads import Spread

ReturnValueDeps = List[List[int]]
ArgumentDeps = List[List[int]]

class Deps():
    """For a function F, F_deps is the set of arguments which may impact the lifetime
    of the returned value(s) of F. In other words, if i \in F_deps, this implies that
    the lifetime of the return value is at most the lifetime of the ith argument to F
    arg_i \in Args.

    Returned values include both the actual return values of the function, as well as
    any mutable arguments that are passed in (as the internal state of these objects)
    may be changed to include references to objects of a shorter lifetime that the
    overall object.
    """

    def __init__(self, R: ReturnValueDeps = None, A: ArgumentDeps = None):
        """Create a representation of F_deps for some function F. If F had a single
        return value, then F_deps could be represented by a single list of indexes S,
        which correspond to the indexes of the arguments which determine the lifetime
        of the return value. For functions with multiple return values, a list of S_j
        is needed for each jth return value. This list is denoted R such that R[j] = S_j

        Additionally, for argumens, the list A is defined in a corresponding manner, where
        A[j] = S_j for each jth argument.
        """
        self.R = R if R is not None else []
        self.A = A if A is not None else []

    def apply_to_parameter_spreads(self, Args: list[Spread]) -> tuple[list[list[Spread]], list[list[Spread]]]:
        """Apply the mapping specified by F_deps to a list Args of parameter spreads. Returns
        a list for each return value of the dependent Args spreads, i.e. arg_i if i \in S_j for
        each return value ret_j
        """
        return ([[arg_i for i, arg_i in enumerate(Args) if i in S_j] for S_j in self.R],
                [[arg_i for i, arg_i in enumerate(Args) if i in S_j] for S_j in self.A])

    def apply_to_parameter_names(self, Args: list[list[str]]) -> list[list[str]]:
        return_names = []
        for S_j in self.R:
            names_possible_for_single_return_value: list[str] = []
            for i in S_j:
                names_possible_for_single_return_value += Args[i]
            return_names.append(names_possible_for_single_return_value)
        return return_names

    def apply_to_parameters_for_arguments(self, Args: list[Any]) -> list[list[Any]]:
        return [[arg_i for i, arg_i in enumerate(Args) if i in S_j] for S_j in self.A]

    def apply_to_parameters_for_return_values(self, Args: list[Any]) -> list[list[Any]]:
        return [[arg_i for i, arg_i in enumerate(Args) if i in S_j] for S_j in self.R]

    def __str__(self) -> str:
        s = "Deps("
        for i, a_spread in enumerate(self.A):
            s += str(i) + ": " + str(a_spread)
        s += ") ->"
        for i, r_spread in enumerate(self.R):
            s += str(i) + ": " + str(r_spread)
        return s


    @classmethod
    def create_from_return_value_spreads(self, RVS: list[Spread], AS: list[Spread] = None) -> Deps:
        """Cannonical way to create F_deps for a non-void function. The list RVS a list
        indexed by return value, where each entry is a set S_i of spreads such that the
        lifetime of return value i depends on entries in S_i
        """
        new_deps = Deps()
        for S_i in RVS:
            new_deps.R.append(S_i.values)
        for S_i in AS:
            new_deps.A.append(S_i.values)
        return new_deps


class FunctionDepsDatabase:
    def __init__(self) -> None:
        self._map: dict[str, Deps] = {}

    @staticmethod
    def get_function_uid_str(instance: EisenInstance):
        return instance.get_full_name()

    def lookup_deps_of(self, function_instance: EisenInstance):
        return self._map.get(FunctionDepsDatabase.get_function_uid_str(function_instance), None)

    def add_deps_for(self, function_instance: EisenInstance, F_deps: Deps):
        # print("added", function_instance)
        self._map[FunctionDepsDatabase.get_function_uid_str(function_instance)] = F_deps
