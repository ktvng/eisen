from __future__ import annotations

from alpaca.clr import CLRList

import eisen.nodes as nodes
from eisen.state.stateb import StateB
from eisen.state.memcheckstate import MemcheckState
State = MemcheckState

from eisen.memory.spreads import Spread, SpreadVisitor

class MemCheck():
    def __init__(self) -> None:
        self.get_deps = GetDeps()

    def run(self, state: StateB):
        self.apply(MemcheckState.create_from_state_b(state))
        return state

    def apply(self, state: State):
        self.get_deps.of_function(state.but_with(asl=MemCheck.get_main_function(state.asl)))

    @classmethod
    def get_main_function(cls, full_asl: CLRList) -> CLRList:
        for child in full_asl:
            if child.type == "def" and child.first().value == "main":
                return child

class Deps():
    """For a function F, F_deps is the set of arguments which may impact the lifetime
    of the returned value(s) of F. In other words, if i \in F_deps, this implies that
    the lifetime of the return value is at most the lifetime of the ith argument to F
    arg_i \in Args
    """

    def __init__(self, R: list[list[int]] = None):
        """Create a representation of F_deps for some function F. If F had a single
        return value, then F_deps could be represented by a single list of indexes S,
        which correspond to the indexes of the arguments which determine the lifetime
        of the return value. For functions with multiple return values, a list of S_j
        is needed for each jth return value. This list is denoted R such that R[j] = S_j
        """
        self.R = R if R is not None else []

    def apply_to_parameter_spreads(self, Args: list[Spread]) -> list[list[Spread]]:
        """Apply the mapping specified by F_deps to a list Args of parameter spreads. Returns
        a list for each return value of the dependent Args spreads, i.e. arg_i if i \in S_j for
        each return value ret_j
        """
        return [[arg_i for i, arg_i in enumerate(Args) if i in S_j]
            for S_j in self.R]

    @classmethod
    def create_from_return_value_spreads(self, RVS: list[Spread]) -> Deps:
        """Cannonical way to create F_deps for a non-void function. The list RVS a list
        index by return value, where each entry is a set S_i of spreads such that the
        lifetime of return value i depends on entries in S_i
        """
        new_deps = Deps()
        for S_i in RVS:
            new_deps.R.append(S_i.values)
        return new_deps


class GetDeps():
    """Representation of the function GET_DEPS: F -> F_Deps with local caching and DP to prevent
    unnecessary lookups.
    """
    def __init__(self):
        self.cache: dict[str, Deps] = {}
        self.spread_visitor = SpreadVisitor(self)

    def _try_cache_lookup(self, state: State) -> Deps | None:
        node = nodes.Def(state)
        function_uid = node.get_function_instance().get_unique_function_name()
        if not state.get_inherited_fns():
            return self.cache.get(function_uid, None)

    def _add_to_cache(self, state: State, F_deps: Deps):
        node = nodes.Def(state)
        function_uid = node.get_function_instance().get_unique_function_name()
        if not state.get_inherited_fns():
            self.cache[function_uid] = F_deps

    def _add_new_spreads_for_inputs(self, state: State):
        """Add new spreads for argument/return values to the function. Argument spreads default
        to only be the argument number, as their lifetime is only dictated by theirselves. Return
        spreads default to the empty set, as there is no information on which arguments dictate
        their lifetimes yet.
        """
        node = nodes.Def(state)
        arg_node = nodes.ArgsRets(state.but_with(asl=node.get_args_asl()))
        for i, name in enumerate(arg_node.get_names()):
            SpreadVisitor.add_spread(state, name, Spread(values={i}, depth=0))

        ret_node = nodes.ArgsRets(state.but_with(asl=node.get_rets_asl()))
        for name in ret_node.get_names():
            SpreadVisitor.add_spread(state, name, Spread(values=set(), depth=0, is_return_value=True))

    def _construct_RVS(self, state: State) -> list[Spread]:
        node = nodes.Def(state)
        ret_node = nodes.ArgsRets(state.but_with(asl=node.get_rets_asl()))
        RVS: list[Spread] = []
        for name in ret_node.get_names():
            spread_for_this_return_value = SpreadVisitor.get_spread(state, name)
            RVS.append(spread_for_this_return_value)
        return RVS

    def of_function(self, state: State) -> Deps:
        """State should have state.get_asl() return an abstract syntax list of type 'def'. This is
        the pointer to F, and this function will return F_deps. Cache lookups will be performed if
        F takes no free function parameters; else novel computation is required.
        """
        cached_f_deps = self._try_cache_lookup(state)
        if cached_f_deps is not None: return cached_f_deps

        # all processing must occur inside an isolate context, to avoid name collisions from
        # previous functions.
        state = state.but_with(context=state.create_isolated_context())
        node = nodes.Def(state)
        self._add_new_spreads_for_inputs(state)

        # invoke the SpreadVisitor to populate all spreads with the correct values after the
        # function call. Depth counts down, starting at -2 (it is underneath the first argument
        # value), and decreasing for each if/while context entered.
        # note: a depth of -1 indicates a literal/token
        self.spread_visitor.apply(state.but_with(
            asl=node.get_seq_asl(),
            depth=-2))

        RVS = self._construct_RVS(state)

        # need to keep this here to examine code inside this function, even though we know
        # it has no return value
        if not node.has_return_value():
            return Deps()

        F_deps = Deps.create_from_return_value_spreads(RVS)
        self._add_to_cache(state, F_deps)
        return F_deps
