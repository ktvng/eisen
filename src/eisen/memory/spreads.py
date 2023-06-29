from __future__ import annotations
from typing import TYPE_CHECKING
from alpaca.utils import Visitor
from alpaca.clr import CLRList
from alpaca.concepts import Type

import eisen.adapters as adapters
from eisen.common.exceptions import Exceptions
from eisen.common import no_assign_binary_ops, boolean_return_ops
from eisen.state.memcheckstate import MemcheckState as State
from eisen.memory.functionalias import FunctionAliasAdder, FunctionAliasResolver
from eisen.memory.possibleparamnames import PossibleParamNamesVisitor

if TYPE_CHECKING:
    from eisen.memory.memcheck import GetDeps
    from eisen.memory.functionalias import CurriedFunction

class Spread():
    def __init__(self, values: set[int], depth: int, is_return_value=False) -> None:
        self.values = values
        self.depth = depth
        self._is_return_value = is_return_value
        self.changed = False

    def __str__(self) -> str:
        return str(self.values)

    def add(self, other: Spread):
        if self.difference(other): self.changed = True
        self.values |= other.values

    def difference(self, other: Spread):
        return (other.values - self.values)

    def is_tainted(self) -> bool:
        """A spread is considered to be tainted if:
            1. The spread is for a return value, and depends on some value local to the
            function (i.e. a value < 0)
            2. The spread is not a return value, and depends on some value from a deeper
            (more negative) context.
        """
        return (any([value < 0 for value in self.values]) and self._is_return_value
            or any([value < self.depth for value in self.values]) and not self._is_return_value)

    def restore(self):
        if self._is_return_value:
            self.values = set([i for i in self.values if i >= 0])
        else:
            self.values = set([i for i in self.values if i >= self.depth])

    def is_return_value(self) -> bool:
        return self._is_return_value

    def is_changed(self) -> bool:
        return self.changed

    @classmethod
    def merge_all(self, spreads: list[Spread]) -> Spread:
        new_spread = Spread(values=set(), depth=None)
        for comp in spreads:
            new_spread.add(comp)
        return new_spread


class SpreadVisitor(Visitor):
    def __init__(self, get_deps: GetDeps):
        super().__init__(False)
        self.get_deps = get_deps

    def apply(self, state: State) -> list[Spread]:
        return self._route(state.asl, state)

    @classmethod
    def get_spread(cls, state: State, name: str) -> Spread:
        """Return a spread for a given local variable name"""
        return state.get_context().get_spread(name)

    @classmethod
    def add_spread(cls, state: State, name: str, spread: Spread):
        """Add a spread for a local variable by name"""
        state.get_context().add_spread(name, spread)

    @Visitor.for_tokens
    def tokens_(fn, state: State):
        """Return the spread for a literal. Literals have depth of -1"""
        return [Spread(values=set(), depth=-1)]

    @Visitor.for_asls("seq")
    def seq_(fn, state: State):
        spreads = []
        for child in state.get_all_children():
            spreads += fn.apply(state.but_with(asl=child))
        return spreads

    @Visitor.for_asls(*boolean_return_ops, *no_assign_binary_ops, '!')
    def binop_(fn, state: State):
        return [Spread(values={state.depth}, depth=state.depth)]

    @Visitor.for_asls("let")
    def decl_(fn, state: State):
        for name in adapters.Decl(state).get_names():
            SpreadVisitor.add_spread(state, name, Spread(values={state.depth}, depth=state.depth))
        return []

    @Visitor.for_asls("var", "val", "var?")
    def decl2_(fn, state: State):
        # because variables can be assigned to anything, they don't have a spread yet
        for name in adapters.Decl(state).get_names():
            SpreadVisitor.add_spread(state, name, Spread(values=set(), depth=state.depth))
        return []

    @Visitor.for_asls("ilet")
    def iletivar_(fn, state: State):
        node = adapters.IletIvar(state)
        FunctionAliasAdder(spread_visitor=fn).apply(state)
        new_spreads = []
        for name in node.get_names():
            new_spread = Spread(values={state.depth}, depth=state.depth)
            SpreadVisitor.add_spread(state, name, new_spread)
            new_spreads.append(new_spread)

        # TODO: fix this!
        # right_spreads = fn.apply(state.but_with_second_child())
        # for name, type, l, r in zip(node.get_names(), node.get_assigned_types(), new_spreads, right_spreads):
        #     # print(">", state.asl, name, l, r)
        #     if type.restriction.is_primitive():
        #         continue
        #     was_tainted = l.is_tainted()
        #     l.add(r)
        #     if not was_tainted and l.is_tainted():
        #         state.report_exception(
        #             Exceptions.ObjectLifetime(
        #                 msg=f"Trying to assign a value to '{name}' with shorter lifetime than '{name}'",
        #                 line_number=state.get_line_number()))
        return []

    @Visitor.for_asls("ivar", "ivar?")
    def iletivar2_(fn, state: State):
        spreads = fn.apply(state.but_with_second_child())
        for name, spread in zip(adapters.IletIvar(state).get_names(), spreads):
            SpreadVisitor.add_spread(state, name, Spread(values=set(spread.values), depth=-2))
        return []

    @Visitor.for_asls(".")
    def dot_(fn, state: State):
        return fn.apply(state.but_with_first_child())

    @Visitor.for_asls("cast")
    def cast_(fn, state: State):
        return fn.apply(state.but_with_first_child())

    @Visitor.for_asls("ref")
    def ref_(fn, state: State):
        return [SpreadVisitor.get_spread(state, adapters.Ref(state).get_name())]

    @Visitor.for_asls("fn", "return")
    def fn_(fn, state: State):
        return []

    @classmethod
    def _get_names_type_and_spreads(cls, fn: SpreadVisitor, state: State) -> tuple[str, Type, Spread, Spread]:
        names = adapters.Assignment(state).get_names_of_parent_objects()
        types = adapters.Assignment(state).get_assigned_types()
        right_spreads = fn.apply(state.but_with_second_child())
        left_spreads = [SpreadVisitor.get_spread(state, name) for name in names]
        return zip(names, types, left_spreads, right_spreads)

    @Visitor.for_asls("=", "+=", "-=", "/=", "*=", "<-")
    def eq_(fn, state: State):
        FunctionAliasAdder(spread_visitor=fn).apply(state)
        left_spreads = []
        for name, type, l, r in SpreadVisitor._get_names_type_and_spreads(fn, state):
            # print("!", state.asl, name, l, r)
            if type.restriction.is_primitive():
                continue
            was_tainted = l.is_tainted()
            l.add(r)
            if not was_tainted and l.is_tainted():
                state.report_exception(
                    Exceptions.ObjectLifetime(
                        msg=f"Trying to assign a value to '{name}' with shorter lifetime than '{name}'",
                        line_number=state.get_line_number()))

            left_spreads.append(l)
        return left_spreads

    @Visitor.for_asls("tuple", "params", "curried")
    def tuple_(fn, state: State):
        spreads = []
        for child in state.get_all_children():
            spreads += fn.apply(state.but_with(asl=child))
        return spreads

    @Visitor.for_asls("if")
    def if_(fn, state: State):
        adapters.If(state.but_with(depth=state.depth-1)).enter_context_and_apply(fn)
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

        # n_iterations = 0
        while (any([spread.is_changed() for spread in spreads])):
            # n_iterations += 1
            for s in spreads: s.changed = False
            # we only want to keep the exceptions thrown after no spreads are changed
            seq_state = cond_state.but_with(
                asl=cond_state.second_child(),
                exceptions=[])
            spreads = fn.apply(seq_state)
            state.exceptions.extend(seq_state.get_exceptions())
        # print(f"REQUIRED {n_iterations} additional iterations of the while loop")
        return []

    @Visitor.for_asls("cond")
    def cond_(fn, state: State):
        cond_context = state.create_block_context()
        state.but_with(
            context=cond_context,
            depth=state.depth-1
                ).apply_fn_to_all_children(fn)
        return []

    @classmethod
    def _get_spreads_of_function_parameters(cls, fn: SpreadVisitor, node: adapters.Call):
        param_spreads = fn.apply(node.state.but_with(asl=node.get_params_asl()))
        _, curried_spreads = FunctionAliasResolver.get_def_asl(node.state)
        return curried_spreads + param_spreads

    @classmethod
    def _get_def_asl(cls, node: adapters.Call):
        def_asl, _ = FunctionAliasResolver.get_def_asl(node.state)
        return def_asl

    @classmethod
    def _get_name_and_parameter_pairs(cls, node: adapters.Call) -> tuple[str, CLRList]:
        def_asl = SpreadVisitor._get_def_asl(node)
        arg_names = adapters.Def(node.state.but_with(asl=def_asl)).get_arg_names()
        params = node.state.but_with(asl=node.get_params_asl()).get_all_children()
        arg_names = arg_names[len(arg_names) - len(params): ]
        return zip(arg_names, params)

    @classmethod
    def _get_inherited_fns(cls, node: adapters.Call) -> dict[str, CurriedFunction]:
        inherited_fns = {}
        # need to ignore curried parameters
        for inside_name, p in SpreadVisitor._get_name_and_parameter_pairs(node):
            param_state = node.state.but_with(asl=p)
            if param_state.is_asl() and param_state.get_returned_type().is_function():
                inherited_fns[inside_name] = (FunctionAliasResolver.get_fn_alias(
                    param_state,
                    adapters.RefLike(param_state).get_name()))
        return inherited_fns

    @Visitor.for_asls("index")
    def index_(fn, state: State):
        return fn.apply(state.but_with_first_child())

    @Visitor.for_asls("curry_call")
    def curry_call_(fn, state: State):
        return []

    @Visitor.for_asls("call", "is_call")
    def call_(fn, state: State):
        node = adapters.Call(state)
        if node.is_print():
            fn.apply(state.but_with_second_child())
            return []

        param_spreads = SpreadVisitor._get_spreads_of_function_parameters(fn, node)
        f_deps = fn.get_deps.of_function(state.but_with(
            asl=SpreadVisitor._get_def_asl(node),
            inherited_fns=SpreadVisitor._get_inherited_fns(node)))
        all_return_value_spreads, all_argument_value_spreads = f_deps.apply_to_parameter_spreads(param_spreads)

        possible_names = [PossibleParamNamesVisitor(fn.get_deps).apply(state.but_with(asl=param))[0]
            for param in node.get_params()]
        types = node.get_param_types()

        # print("========")
        # print(state.get_asl())
        # print()
        # print(all_argument_value_spreads[0][0])

        for type, possible_names, spreads_for_one_argument in zip(types, possible_names, all_argument_value_spreads):
            for name in possible_names:
                l = SpreadVisitor.get_spread(state, name)
                was_tainted = l.is_tainted()
                l.add(Spread.merge_all(spreads_for_one_argument))
                if not was_tainted and l.is_tainted() and not type.restriction.is_primitive():
                    state.report_exception(
                        Exceptions.ObjectLifetime(
                            msg=f"Trying to assign a value to '{name}' with shorter lifetime than '{name}'",
                            line_number=state.get_line_number()))

        return [Spread.merge_all(spreads_for_one_return_value)
            for spreads_for_one_return_value in all_return_value_spreads]

    @Visitor.for_default
    def default_(fn, state: State):
        print(f"SpreadVisitor Unhandled state {state.asl}")
        exit()
        return []