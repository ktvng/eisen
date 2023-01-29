from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.clr import CLRList
from alpaca.concepts import Type

import eisen.nodes as nodes
from eisen.common.exceptions import Exceptions
from eisen.common.eiseninstance import EisenFunctionInstance
from eisen.common import no_assign_binary_ops, boolean_return_ops
from eisen.state.stateb import StateB
from eisen.state.memcheckstate import MemcheckState

State = MemcheckState

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

    @classmethod
    def get_spread(cls, state: MemcheckState, name: str) -> Spread:
        return state.get_context().get_spread(name)

    @classmethod
    def add_spread(cls, state: MemcheckState, name: str, spread: Spread):
        state.get_context().add_spread(name, spread)


class Spread():
    def __init__(self, values: set[int], depth: int, is_return_value=False) -> None:
        self.values = values
        self.depth = depth
        self._is_return_value = is_return_value
        self.changed = False

    def __str__(self) -> str:
        return str(self.values)

    def add(self, other: Spread):
        if self.difference(other):
            self.changed = True
        self.values |= other.values

    def difference(self, other: Spread):
        return (other.values - self.values)

    def is_tainted(self) -> bool:
        return (any([value < 0 for value in self.values]) and self._is_return_value
            or any([value < self.depth for value in self.values]) and not self._is_return_value)

    def is_return_value(self) -> bool:
        return self._is_return_value

    @classmethod
    def merge_all(self, spreads: list[Spread]) -> Spread:
        new_spread = Spread(values=set(), depth=None)
        for comp in spreads:
            new_spread.add(comp)
        return new_spread

class Deps():
    def __init__(self, indexes_by_return_value: list = None):
        indexes_by_return_value = indexes_by_return_value or []
        self.indexes_by_return_value = indexes_by_return_value

    def apply_to_parameter_spreads(self, param_spreads: list[Spread]) -> list[list[Spread]]:
        return [[x for i, x in enumerate(param_spreads) if i in indexes_for_a_return_val]
            for indexes_for_a_return_val in self.indexes_by_return_value]

    @classmethod
    def create_from_return_value_spreads(self, return_value_spreads: list[Spread]) -> Deps:
        new_deps = Deps()
        for spread in return_value_spreads:
            new_deps.indexes_by_return_value.append(spread.values)
        return new_deps


class GetDeps():
    def __init__(self):
        self.cache: dict[str, Deps] = {}
        self.spread_visitor = SpreadVisitor(self)

    def of_function(self, state: State) -> Deps:
        node = nodes.Def(state)
        function_uid = node.get_function_instance().get_unique_function_name()
        found_deps = self.cache.get(function_uid, None)
        if found_deps is not None:
            return found_deps

        # Main start
        state = state.but_with(context=state.create_block_context())

        input_number = 0
        def_node = nodes.Def(state)

        # add the spread of all inputs to the function to be the index of that input
        arg_node = nodes.ArgsRets(state.but_with(asl=def_node.get_args_asl()))
        for name in arg_node.get_names():
            MemCheck.add_spread(state, name, Spread(values={input_number}, depth=0))
            input_number += 1

        ret_node = nodes.ArgsRets(state.but_with(asl=def_node.get_rets_asl()))
        for name in ret_node.get_names():
            MemCheck.add_spread(state, name, Spread(values=set(), depth=0, is_return_value=True))
            input_number += 1

        self.spread_visitor.apply(state.but_with(
            asl=def_node.get_seq_asl(),
            depth=-1))

        spreads_for_return_values: list[Spread] = []
        for name in ret_node.get_names():
            spread_for_this_return_value = MemCheck.get_spread(state, name)
            spreads_for_return_values.append(spread_for_this_return_value)

        if not node.has_return_value():
            return Deps()

        new_deps = Deps.create_from_return_value_spreads(spreads_for_return_values)
        self.cache[function_uid] = new_deps
        return new_deps

class CurriedFunction():
    def __init__(self, fn_instance: EisenFunctionInstance, param_spreads: list[Spread]) -> None:
        self.fn_instance = fn_instance
        self.param_spreads = param_spreads if param_spreads is not None else []

class FunctionAliasAdder(Visitor):
    def __init__(self, spread_visitor: SpreadVisitor, debug: bool = False):
        super().__init__(debug)
        self.spread_visitor = spread_visitor

    def apply(self, state: State) -> CurriedFunction:
        return self._route(state.asl, state)

    @Visitor.for_asls("ilet")
    def ilet_(fn, state: State):
        node = nodes.IletIvar(state)
        if not isinstance(state.second_child(), CLRList):
            return

        type = state.but_with_second_child().get_returned_type()
        if not type.is_function():
            return
        fn_thing = fn.apply(state.but_with_second_child())
        for name in node.get_names():
            FunctionAliasAdder.add_fn_alias(state, name, fn_thing)

    @Visitor.for_asls("+=", "-=", "*=", "/=", "<-")
    def assign_(fn, state: State):
        return

    @Visitor.for_asls("=")
    def eq_(fn, state: State):
        type = state.but_with_first_child().get_returned_type()
        if not type.is_function():
            return
        node = nodes.Assignment(state)
        fn_thing = fn.apply(state.but_with_second_child())
        for name in node.get_names_of_parent_objects():
            FunctionAliasAdder.add_fn_alias(state, name, fn_thing)

    @Visitor.for_asls("fn")
    def fn_(fn, state: State):
        node = nodes.Fn(state)
        return CurriedFunction(node.resolve_function_instance(state.get_argument_type()), [])

    @Visitor.for_asls("ref")
    def ref_(fn, state: State):
        node = nodes.Ref(state)
        return FunctionAliasResolver.get_fn_alias(state, node.get_name())

    @Visitor.for_asls("curry_call")
    def curry_call_(fn, state: State):
        node = nodes.CurriedCall(state)
        param_spreads = fn.spread_visitor.apply(state.but_with(asl=node.get_params_asl()))
        fn_thing = fn.apply(state.but_with_first_child())
        fn_thing.param_spreads = param_spreads
        return fn_thing

    @classmethod
    def add_fn_alias(cls, state: State, name: str, fn: CurriedFunction):
        state.get_context().add_fn_alias(name, fn)

class FunctionAliasResolver:
    @classmethod
    def get_def_asl(cls, state: State) -> tuple[CLRList, list[Spread]]:
        if state.first_child().type == "ref":
            fn_thing = FunctionAliasResolver.get_fn_alias(
                state,
                nodes.Ref(state.but_with_first_child()).get_name())
            return fn_thing.fn_instance.asl, fn_thing.param_spreads
        return state.but_with_first_child().get_instances()[0].asl, []

    @classmethod
    def get_fn_alias(cls, state: State, name: str) -> CurriedFunction:
        return state.get_context().get_fn_alias(name)



class SpreadVisitor(Visitor):
    def __init__(self, get_deps: GetDeps):
        super().__init__(False)
        self.get_deps = get_deps

    def apply(self, state: State) -> list[Spread]:
        return self._route(state.asl, state)

    @Visitor.for_tokens
    def tokens_(fn, state: State):
        return [Spread(values=set(), depth=0)]

    @Visitor.for_asls("seq")
    def seq_(fn, state: State):
        spreads = []
        for child in state.get_all_children():
            spreads += fn.apply(state.but_with(asl=child))
        return spreads

    @Visitor.for_asls(*boolean_return_ops, *no_assign_binary_ops, '!', 'cast')
    def binop_(fn, state: State):
        return [Spread(values={state.depth}, depth=state.depth)]

    @Visitor.for_asls("let")
    def decl_(fn, state: State):
        for name in nodes.Decl(state).get_names():
            MemCheck.add_spread(state, name, Spread(values={state.depth}, depth=state.depth))
        return []

    @Visitor.for_asls("var", "val", "var?")
    def decl2_(fn, state: State):
        # because variables can be assigned to anything, they don't have a spread yet
        for name in nodes.Decl(state).get_names():
            MemCheck.add_spread(state, name, Spread(values=set(), depth=state.depth))
        return []

    @Visitor.for_asls("ilet")
    def iletivar_(fn, state: State):
        FunctionAliasAdder(spread_visitor=fn).apply(state)
        for name in nodes.IletIvar(state).get_names():
            MemCheck.add_spread(state, name, Spread(values={state.depth}, depth=state.depth))
        return []

    @Visitor.for_asls("ivar")
    def iletivar2_(fn, state: State):
        for name in nodes.IletIvar(state).get_names():
            MemCheck.add_spread(state, name, Spread(values=set(), depth=state.depth))
        return []

    @Visitor.for_asls(".")
    def dot_(fn, state: State):
        return fn.apply(state.but_with_first_child())

    @Visitor.for_asls("ref")
    def ref_(fn, state: State):
        return [MemCheck.get_spread(state, nodes.Ref(state).get_name())]

    @Visitor.for_asls("fn")
    def fn_(fn, state: State):
        return []

    @Visitor.for_asls("=", "+=", "-=", "/=", "*=", "<-")
    def eq_(fn, state: State):
        FunctionAliasAdder(spread_visitor=fn).apply(state)
        names = nodes.Assignment(state).get_names_of_parent_objects()
        assigned_spreads = fn.apply(state.but_with_second_child())
        left_spreads = []
        for name, right_spread in zip(names, assigned_spreads):
            left_spread = MemCheck.get_spread(state, name)
            left_spread.add(right_spread)

            # TODO fix this, doesn't work for tuples
            if left_spread.is_tainted() and not state.but_with_first_child().get_restriction().is_primitive():
                state.report_exception(
                    Exceptions.ObjectLifetime(
                        msg=f"Trying to assign a value to '{name}' with shorter lifetime than '{name}'",
                        line_number=state.get_line_number()))

            left_spreads.append(left_spread)
        return left_spreads

    @Visitor.for_asls("tuple", "params", "curried")
    def tuple_(fn, state: State):
        spreads = []
        for child in state.get_all_children():
            spreads += fn.apply(state.but_with(asl=child))
        return spreads

    @Visitor.for_asls("if")
    def if_(fn, state: State):
        nodes.If(state.but_with(depth=state.depth-1)).enter_context_and_apply(fn)
        return []

    @Visitor.for_asls("while")
    def while_(fn, state: State):
        cond_state = state.but_with(
            asl=state.first_child(),
            context=state.create_block_context(),
            depth=state.depth-1)

        # no spreads can change in the first part of the cond, as there is no assignment
        fn.apply(cond_state.but_with_first_child())
        spreads = fn.apply(cond_state.but_with_second_child())

        # TODO: we use this to prevent duplicate exceptions. make this cleaner
        # local exceptions are used because we iterate over the while loop multiple
        # times and each time can throw an exception
        cond_state.exceptions = []
        local_exceptions = []
        n_iterations = 0
        while (any([spread.changed for spread in spreads])):
            n_iterations += 1
            for s in spreads:
                s.changed = False
            spreads = fn.apply(cond_state.but_with_second_child())
            local_exceptions = cond_state.exceptions
            cond_state.exceptions = []

        state.exceptions.extend(local_exceptions)
        print(f"REQUIRED {n_iterations} additional iterations of the while loop")

        return []

    @Visitor.for_asls("cond")
    def cond_(fn, state: State):
        cond_context = state.create_block_context()
        state.but_with(
            context=cond_context,
            depth=state.depth-1
                ).apply_fn_to_all_children(fn)
        return []

    @Visitor.for_asls("call", "is_call")
    def call_(fn, state: State):
        node = nodes.Call(state)
        if node.is_print():
            fn.apply(state.but_with_second_child())
            return []

        param_spreads = fn.apply(state.but_with(asl=node.get_params_asl()))
        def_asl, curried_spreads = FunctionAliasResolver.get_def_asl(state)
        param_spreads = curried_spreads + param_spreads

        f_deps = fn.get_deps.of_function(state.but_with(asl=def_asl))
        all_return_value_spreads = f_deps.apply_to_parameter_spreads(param_spreads)
        return [Spread.merge_all(spreads_for_one_return_value)
            for spreads_for_one_return_value in all_return_value_spreads]

    @Visitor.for_default
    def default_(fn, state: State):
        print(f"MemCheck Unhandled state {state.asl}")
        return []
