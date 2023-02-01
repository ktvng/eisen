from __future__ import annotations
from typing import TYPE_CHECKING
from alpaca.utils import Visitor
from alpaca.clr import CLRList

import eisen.nodes as nodes
from eisen.common.eiseninstance import EisenFunctionInstance
from eisen.state.memcheckstate import MemcheckState as State

if TYPE_CHECKING:
    from eisen.memory.spreads import SpreadVisitor, Spread

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

    # TODO: make this work
    @Visitor.for_asls("call")
    def call_(fn, state: State):
        param_spreads = fn.spread_visitor.apply(state)
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
            name = nodes.Ref(state.but_with_first_child()).get_name()
            fn_thing = FunctionAliasResolver.get_fn_alias(
                state,
                name)
            if fn_thing is None:
               fn_thing = state.get_inherited_fns().get(name, None)
            if fn_thing is None:
                raise Exception(f"did not find curried function with name {name}")
            return fn_thing.fn_instance.asl, fn_thing.param_spreads
        return state.but_with_first_child().get_instances()[0].asl, []

    @classmethod
    def get_fn_alias(cls, state: State, name: str) -> CurriedFunction:
        return state.get_context().get_fn_alias(name)
