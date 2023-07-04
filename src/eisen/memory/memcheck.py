from __future__ import annotations
from alpaca.clr import CLRList

from alpaca.utils import Visitor

import eisen.adapters as adapters
from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor
from eisen.state.state_postspreadvisitor import State_PostSpreadVisitor
from eisen.state.memcheckstate import MemcheckState

from eisen.memory.spreads import Spread, SpreadVisitor
from eisen.memory.deps import FunctionDepsDatabase, Deps

State = MemcheckState

class MemCheck(Visitor):
    def __init__(self, debug: bool = False):
        super().__init__(debug=debug)
        self.get_deps = None

    def run(self, state: State_PostInstanceVisitor) -> State_PostSpreadVisitor:
        self.get_deps = GetDeps(state)
        internal_state = MemcheckState.create_from_basestate(state)

        self.get_deps.of_function(internal_state.but_with(asl=MemCheck.get_main_function(state.asl)))
        self.apply(internal_state)
        return State_PostSpreadVisitor.create_from_basestate(state, self.get_deps.cache)

    def apply(self, state: State):
        self._route(state.get_asl(), state)

    @Visitor.for_asls("start")
    def _start(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_asls("mod")
    def _mod(fn, state: State):
        adapters.Mod(state).enter_module_and_apply(fn)

    @Visitor.for_asls("def", "create", "is_fn")
    def _def(fn, state: State):
        fn.get_deps.of_function(state)

    @Visitor.for_asls("struct")
    def _create(fn, state: State):
        node = adapters.Struct(state)
        if node.has_create_asl():
            fn.apply(state.but_with(asl=node.get_create_asl()))

    @Visitor.for_asls("variant")
    def _variant(fn, state: State):
        node = adapters.Variant(state)
        fn.apply(state.but_with(asl=node.get_is_asl()))

    @Visitor.for_asls("interface")
    def _nothing(fn, state: State):
        return

    @classmethod
    def get_main_function(cls, full_asl: CLRList) -> CLRList:
        for child in full_asl:
            if child.type == "def" and child.first().value == "main":
                return child

class GetDeps():
    """Representation of the function GET_DEPS: F -> F_Deps with local caching and DP to prevent
    unnecessary lookups.
    """
    def __init__(self, state: State):
        self.cache = FunctionDepsDatabase()
        self.spread_visitor = SpreadVisitor(self)
        self._add_builtin_function_deps(state)

    def _add_builtin_function_deps(self, state: State):
        for builtin_func_instance in state.get_all_builtins():
            self.cache.add_deps_for(builtin_func_instance, F_deps=Deps(
                R = [[0]],
                A = [[0], []]))

    def _try_cache_lookup(self, state: State) -> Deps | None:
        node = adapters.Def(state)
        if not state.get_inherited_fns():
            return self.cache.lookup_deps_of(node.get_function_instance())

    def _add_to_cache(self, state: State, F_deps: Deps):
        node = adapters.Def(state)
        if not state.get_inherited_fns():
            self.cache.add_deps_for(node.get_function_instance(), F_deps)

    def _add_new_spreads_for_inputs(self, state: State):
        """Add new spreads for argument/return values to the function. Argument spreads default
        to only be the argument number, as their lifetime is only dictated by theirselves. Return
        spreads default to the empty set, as there is no information on which arguments dictate
        their lifetimes yet.
        """
        node = adapters.Def(state)
        arg_node = adapters.ArgsRets(state.but_with(asl=node.get_args_asl()))
        for i, name in enumerate(arg_node.get_names()):
            SpreadVisitor.add_spread(state, name, Spread(values={i}, depth=0))

        ret_node = adapters.ArgsRets(state.but_with(asl=node.get_rets_asl()))
        for name in ret_node.get_names():
            SpreadVisitor.add_spread(state, name, Spread(values=set(), depth=0, is_return_value=True))

    def _construct_RVS(self, state: State) -> list[Spread]:
        node = adapters.Def(state)
        ret_node = adapters.ArgsRets(state.but_with(asl=node.get_rets_asl()))
        RVS: list[Spread] = []
        for name in ret_node.get_names():
            spread_for_this_return_value = SpreadVisitor.get_spread(state, name)
            RVS.append(spread_for_this_return_value)

        return RVS

    def _construct_AS(self, state: State) -> list[Spread]:
        node = adapters.Def(state)
        arg_node = adapters.ArgsRets(state.but_with(asl=node.get_args_asl()))
        AS: list[Spread] = []
        for name in arg_node.get_names():
            spread_for_this_argument = SpreadVisitor.get_spread(state, name)
            AS.append(spread_for_this_argument)

        return AS

    def of_function(self, state: State) -> Deps:
        """State should have state.get_asl() return an abstract syntax list of type 'def'. This is
        the pointer to F, and this function will return F_deps. Cache lookups will be performed if
        F takes no free function parameters; else novel computation is required.
        """
        # print("getting deps for", adapters.Def(state).get_function_name())
        cached_f_deps = self._try_cache_lookup(state)
        if cached_f_deps is not None: return cached_f_deps
        print("no cache found")

        # all processing must occur inside an isolate context, to avoid name collisions from
        # previous functions.
        state = state.but_with(context=state.create_isolated_context())
        node = adapters.Def(state)
        self._add_new_spreads_for_inputs(state)

        # invoke the SpreadVisitor to populate all spreads with the correct values after the
        # function call. Depth counts down, starting at -2 (it is underneath the first argument
        # value), and decreasing for each if/while context entered.
        # note: a depth of -1 indicates a literal/token
        self.spread_visitor.apply(state.but_with(
            asl=node.get_seq_asl(),
            depth=-2))

        RVS = self._construct_RVS(state)
        AS = self._construct_AS(state)

        # # need to keep this here to examine code inside this function, even though we know
        # # it has no return value
        # if not node.has_return_value():
        #     return Deps()

        F_deps = Deps.create_from_return_value_spreads(RVS, AS)
        self._add_to_cache(state, F_deps)
        return F_deps
