from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.clr import CLRList

from eisen.validation.nodetypes import Nodes
from eisen.common.exceptions import Exceptions
from eisen.common.state import State
from eisen.common import no_assign_binary_ops, boolean_return_ops

class PublicCheck():
    def __init__(self) -> None:
        self.get_deps = GetDeps()

    def apply(self, state: State):
        self.get_deps.of_function(state.but_with(asl=PublicCheck.get_main_function(state.asl)))

    @classmethod
    def get_main_function(cls, full_asl: CLRList) -> CLRList:
        for child in full_asl:
            if child.type == "def" and child.first().value == "main":
                return child

class Spread():
    def __init__(self, values: set[int], depth: int, is_return_value=False) -> None:
        self.values = values
        self.depth = depth
        self._is_return_value = is_return_value
        self.changed = False

    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Spread) and __o.value == self.value;

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
    def __init__(self, indexes_by_return_value: list = []):
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
        node = Nodes.Def(state)
        function_uid = node.get_function_instance().get_unique_function_name()
        found_deps = self.cache.get(function_uid, None)
        if found_deps is not None:
            return found_deps

        # Main start
        state = state.but_with(context=state.create_block_context("func"))

        input_number = 0
        def_node = Nodes.Def(state)

        # add the spread of all inputs to the function to be the index of that input
        arg_node = Nodes.ArgsRets(state.but_with(asl=def_node.get_args_asl()))
        for name in arg_node.get_names():
            state.add_spread(name, Spread(values={input_number}, depth=0))
            input_number += 1

        ret_node = Nodes.ArgsRets(state.but_with(asl=def_node.get_rets_asl()))
        for name in ret_node.get_names():
            state.add_spread(name, Spread(values=set(), depth=0, is_return_value=True))
            input_number += 1

        self.spread_visitor.apply(state.but_with(
            asl=def_node.get_seq_asl(),
            depth=-1))

        spreads_for_return_values: list[Spread] = []
        for name in ret_node.get_names():
            spread_for_this_return_value = state.get_spread(name)
            spreads_for_return_values.append(spread_for_this_return_value)

        if not node.has_return_value():
            return Deps()

        new_deps = Deps.create_from_return_value_spreads(spreads_for_return_values)
        self.cache[function_uid] = new_deps
        return new_deps

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
        for name in Nodes.Decl(state).get_names():
            state.add_spread(name, Spread(values={state.depth}, depth=state.depth))
        return []

    @Visitor.for_asls("var", "val", "var?")
    def decl2_(fn, state: State):
        # because variables can be assigned to anything, they don't have a spread yet
        for name in Nodes.Decl(state).get_names():
            state.add_spread(name, Spread(values=set(), depth=state.depth))
        return []

    @Visitor.for_asls("ilet")
    def iletivar_(fn, state: State):
        for name in Nodes.IletIvar(state).get_names():
            state.add_spread(name, Spread(values={state.depth}, depth=state.depth))
        return []

    @Visitor.for_asls("ivar")
    def iletivar2_(fn, state: State):
        for name in Nodes.IletIvar(state).get_names():
            state.add_spread(name, Spread(values=set(), depth=state.depth))
        return []

    @Visitor.for_asls("ref")
    def ref_(fn, state: State):
        return [state.get_spread(Nodes.Ref(state).get_name())]

    @Visitor.for_asls("=", "+=", "-=", "/=", "*=", "<-")
    def eq_(fn, state: State):
        names = Nodes.Assignment(state).get_names_of_parent_objects()
        assigned_spreads = fn.apply(state.but_with_second_child())
        left_spreads = []
        for name, right_spread in zip(names, assigned_spreads):
            left_spread = state.get_spread(name)
            left_spread.add(right_spread)

            if left_spread.is_tainted():
                state.report_exception(
                    Exceptions.ObjectLifetime(
                        msg=f"Trying to assign a value to '{name}' with shorter lifetime than '{name}'",
                        line_number=state.get_line_number()))

            left_spreads.append(left_spread)
        return left_spreads

    @Visitor.for_asls("tuple", "params")
    def tuple_(fn, state: State):
        spreads = []
        for child in state.get_all_children():
            spreads += fn.apply(state.but_with(asl=child))
        return spreads

    @Visitor.for_asls("if")
    def if_(fn, state: State):
        for child in state.get_all_children():
            if child.type == "seq":
                fn.apply(state.but_with(
                    asl=child,
                    context=state.create_block_context("if"),
                    depth = state.depth-1))
            fn.apply(state.but_with(asl=child))
        return []

    @Visitor.for_asls("while")
    def while_(fn, state: State):
        cond_state = state.but_with(
            asl=state.first_child(),
            context=state.create_block_context("cond"),
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
        cond_context = state.create_block_context("cond")
        state.but_with(
            context=cond_context,
            depth=state.depth-1
                ).apply_fn_to_all_children(fn)
        return []

    @Visitor.for_asls("call")
    def call_(fn, state: State):
        node = Nodes.Call(state)
        if node.is_print():
            return []
        def_asl = node.get_asl_defining_the_function()
        f_deps = fn.get_deps.of_function(state.but_with(asl=def_asl))
        all_return_value_spreads = f_deps.apply_to_parameter_spreads(
            param_spreads=fn.apply(state.but_with(asl=node.get_params_asl())))
        return [Spread.merge_all(spreads_for_one_return_value)
            for spreads_for_one_return_value in all_return_value_spreads]
