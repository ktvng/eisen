from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.clr import CLRList

from eisen.validation.nodetypes import Nodes
from eisen.common.exceptions import Exceptions
from eisen.common.state import State

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
