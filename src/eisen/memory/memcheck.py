from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.clr import CLRList

from eisen.validation.nodetypes import Nodes
from eisen.common.exceptions import Exceptions
from eisen.common.state import State

class PublicCheck():
    def apply(cls, state: State):
        # state.simple_check = SimpleMemCheck()
        # state.recursion_check = RecursionMemCheck()
        # result = state.simple_check.apply(state.but_with(
        #     asl=PublicCheck.get_main_function(state.asl),
        #     context=state.create_block_context("func")))
        # print(result.ok)

        get_deps = GetDeps()
        get_deps.of_function(state.but_with(asl=PublicCheck.get_main_function(state.asl)))

    @classmethod
    def get_main_function(cls, full_asl: CLRList) -> CLRList:
        for child in full_asl:
            if child.type == "def" and child.first().value == "main":
                return child

class MemCheckResult():
    def __init__(self, ok: bool):
        self.ok = ok

class CallManager():
    @classmethod
    def is_recursive(cls, state: State):
        return False

    @classmethod
    def process_call(cls, state: State) -> MemCheckResult:
        # TODO: implement recusion support
        if not CallManager.is_recursive(state):
            node = Nodes.Call(state)
            return state.simple_check.apply(state.but_with(asl=node.get_asl_defining_the_function()))

class DepthCheck(Visitor):
    def apply(self, state: State) -> list[int]:
        return self._route(state.asl, state)

    @Visitor.for_tokens
    def tokens_(fn, state: State):
        return [state.depth]

    @Visitor.for_asls("ref")
    def ref_(fn, state: State):
        return [state.get_context().get_depth(Nodes.Ref(state).get_name())]

    @Visitor.for_asls("tuple", "params")
    def tuple_(fn, state: State):
        aggregate = []
        for child in state.get_all_children():
            aggregate += fn.apply(state.but_with(asl=child))
        return aggregate

    @Visitor.for_asls("cast")
    def cast_(fn, state: State):
        return fn.apply(state.but_with_first_child())

    @Visitor.for_asls("call")
    def call_(fn, state: State):
        node = Nodes.Call(state)
        if node.is_print():
            return []

        new_state = state.but_with(
            context=state.create_block_context("func"),
            depth=state.depth+1)

        param_depths = fn.apply(state.but_with(asl=node.get_params_asl()))
        for name, depth in zip(node.get_param_names(), param_depths):
            new_state.get_context().add_depth(name, depth)

        # TODO: figure this out
        return_depths = [0] * len(node.get_return_names())
        for name, depth in zip(node.get_return_names(), return_depths):
            new_state.get_context().add_depth(name, depth)

        CallManager.process_call(new_state)
        # TODO: fix this for tuple returns
        # TODO: a call should always return something of the right depth.
        return [-1]


class SimpleMemCheck(Visitor):
    def __init__(self):
        super().__init__()
        self.depth_check = DepthCheck()

    def apply(self, state: State) -> MemCheckResult:
        return self._route(state.asl, state)

    @classmethod
    def validate_depths(cls, state: State, l_depths: list[int], r_depths: list[int]) -> MemCheckResult:
        result = MemCheckResult(ok=all([l >= r for l, r in zip(l_depths, r_depths)]))
        if not result.ok:
            state.report_exception(Exceptions.ObjectLifetime("todo: message", state.get_line_number()))
        return result

    @Visitor.for_asls("let", "val", "var")
    def let_(fn, state: State):
        node = Nodes.Decl(state)
        for name in node.get_names():
            state.get_context().add_depth(name, state.depth)
        return MemCheckResult(ok=True)

    @Visitor.for_asls("ilet", "ivar")
    def _ilet(fn, state: State):
        node = Nodes.IletIvar(state)
        for name in node.get_names():
            state.get_context().add_depth(name, state.depth)

        l_depths = [state.depth] * len(node.get_names())
        r_depths = fn.depth_check.apply(state.but_with_second_child())
        return SimpleMemCheck.validate_depths(state, l_depths, r_depths)


    @Visitor.for_asls("=", "+=", "-=", "/=", "*=", "<-")
    def eqs_(fn, state: State):
        if state.get_returned_type().is_novel() and state.get_restriction().is_primitive():
            return MemCheckResult(ok=True)

        l_depths = fn.depth_check.apply(state.but_with_first_child())
        r_depths = fn.depth_check.apply(state.but_with_second_child())
        print(state.asl, l_depths, r_depths)
        return SimpleMemCheck.validate_depths(state, l_depths, r_depths)

    @Visitor.for_asls("if", "create", "while")
    def if_(fn, state: State):
        # TODO
        return MemCheckResult(ok=True)

    @Visitor.for_asls("seq")
    def seq_(fn, state: State):
        result = MemCheckResult(ok=True)
        for child in state.get_child_asls():
            child_result = fn.apply(state.but_with(asl=child))
            result.ok = result.ok and child_result.ok
        return result

    @Visitor.for_asls("def")
    def def_(fn, state: State):
        return fn.apply(state.but_with(asl=Nodes.Def(state).get_seq_asl()))

    @Visitor.for_asls("call")
    def call_(fn, state: State):
        fn.depth_check.apply(state)
        return MemCheckResult(ok=True)


    # @Visitor.for_asls("call")
    # def call_(fn, state: State):
    #     return CallManager.process_call(state)





class RecursionMemCheck(Visitor):
    def apply(self, state: State):
        return self._route(state.asl, state)

class Spread():
    def __init__(self, values: set[int]) -> None:
        self.values = values

    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Spread) and __o.value == self.value;

    def __str__(self) -> str:
        return str(self.values)

    def add(self, other: Spread):
        self.values |= other.values

    def is_tainted(self) -> bool:
        return -1 in self.values

    @classmethod
    def merge_all(self, spreads: list[Spread]) -> Spread:
        new_spread = Spread(values=set())
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

        # kxt debug
        print("called of function with", state.asl)

        # Main start
        state = state.but_with(context=state.create_block_context("func"))

        input_number = 0
        def_node = Nodes.Def(state)

        # add the spread of all inputs to the function to be the index of that input
        arg_node = Nodes.ArgsRets(state.but_with(asl=def_node.get_args_asl()))
        for name in arg_node.get_names():
            state.add_spread(name, Spread(values={input_number}))
            input_number += 1

        ret_node = Nodes.ArgsRets(state.but_with(asl=def_node.get_rets_asl()))
        for name in ret_node.get_names():
            state.add_spread(name, Spread(values=set()))
            input_number += 1

        self.spread_visitor.apply(state.but_with(asl=def_node.get_seq_asl()))

        # kxt debug
        all_spreads = state.get_context().containers["spread"]
        for k, v in all_spreads.items():
            print(k, v)


        spreads_for_return_values: list[Spread] = []
        for name in ret_node.get_names():
            spread_for_this_return_value = state.get_spread(name)
            spreads_for_return_values.append(spread_for_this_return_value)
            if spread_for_this_return_value.is_tainted():
                state.report_exception(Exceptions.ObjectLifetime(f"{name} is tainted. TODO: better message", state.get_line_number()))

        if not node.has_return_value():
            return Deps()

        new_deps = Deps.create_from_return_value_spreads(spreads_for_return_values)
        return new_deps

class SpreadVisitor(Visitor):
    def __init__(self, get_deps: GetDeps):
        super().__init__(False)
        self.get_deps = get_deps

    def apply(self, state: State) -> list[Spread]:
        return self._route(state.asl, state)

    @Visitor.for_asls("seq")
    def seq_(fn, state: State):
        state.apply_fn_to_all_children(fn)
        return []

    @Visitor.for_asls("<")
    def binop_(fn, state: State):
        return [Spread(values={-1})]

    @Visitor.for_asls("let", "var", "val", "var?")
    def decl_(fn, state: State):
        for name in Nodes.Decl(state).get_names():
            state.add_spread(name, Spread(values={-1}))
        return []

    @Visitor.for_asls("ilet", "ivar")
    def iletivar_(fn, state: State):
        for name in Nodes.IletIvar(state).get_names():
            state.add_spread(name, Spread(values={-1}))
        return []

    @Visitor.for_asls("ref")
    def ref_(fn, state: State):
        return [state.get_spread(Nodes.Ref(state).get_name())]

    @Visitor.for_asls("=")
    def eq_(fn, state: State):
        names = Nodes.Assignment(state).get_names()
        assigned_spreads = fn.apply(state.but_with_second_child())
        for name, right_spread in zip(names, assigned_spreads):
            left_spread = state.get_spread(name)
            left_spread.add(right_spread)

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
                    context=state.create_block_context("if")))
            fn.apply(state.but_with(asl=child))

    @Visitor.for_asls("cond")
    def cond_(fn, state: State):
        cond_context = state.create_block_context("cond")
        state.but_with(context=cond_context).apply_fn_to_all_children(fn)

    @Visitor.for_asls("call")
    def call_(fn, state: State):
        node = Nodes.Call(state)
        def_asl = node.get_asl_defining_the_function()
        f_deps = fn.get_deps.of_function(state.but_with(asl=def_asl))
        all_return_value_spreads = f_deps.apply_to_parameter_spreads(
            param_spreads=fn.apply(state.but_with(asl=node.get_params_asl())))
        return [Spread.merge_all(spreads_for_one_return_value)
            for spreads_for_one_return_value in all_return_value_spreads]
