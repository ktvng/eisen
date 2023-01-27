from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.concepts import Type

import eisen.nodes as nodes
from eisen.common.eiseninstance import EisenInstance
from eisen.state.statea import StateA
from eisen.state.stateb import StateB
from eisen.state.instancevisitorstate import InstanceVisitorState

State = InstanceVisitorState

class InstanceVisitor(Visitor):
    """creates and persists instances for terminal asls"""

    def run(self, state: StateA):
        self.apply(InstanceVisitorState.create_from_state_A(state))
        return StateB.create_from_state_a(state)

    def apply(self, state: State) -> list[EisenInstance]:
        result: list[EisenInstance] = self._route(state.get_asl(), state)
        if result:
            state.get_node_data().instances = result
        return result

    @classmethod
    def create_instance_inside_context(cls, name: str, type: Type, state: State):
        """add a new instance to the current context and return it."""
        instance = EisenInstance(
            name=name,
            type=type,
            context=state.get_context(),
            asl=state.get_asl(),
            # TODO: fix this abuse of as_ptr
            is_ptr=state.is_ptr)
        state.get_context().add_instance(instance)
        return instance

    @Visitor.for_tokens
    def token_(fn, state: State) -> list[EisenInstance]:
        return []

    @Visitor.for_asls("interface")
    def no_action_(fn, state: State) -> list[EisenInstance]:
        return []

    @Visitor.for_default
    def continue_(fn, state: State) -> list[EisenInstance]:
        state.apply_fn_to_all_children(fn)
        return []

    @Visitor.for_asls("mod")
    def mod_(fn, state: State) -> list[EisenInstance]:
        nodes.Mod(state).enter_module_and_apply(fn)
        return []

    @Visitor.for_asls("ref", "fn")
    def ref_(fn, state: State) -> list[EisenInstance]:
        return [nodes.Ref(state).resolve_instance()]

    @Visitor.for_asls("rets", "args")
    def rets_(fn, state: State) -> list[EisenInstance]:
        for child in state.get_child_asls():
            fn.apply(state.but_with(asl=child, is_ptr=True))
        return []

    @Visitor.for_asls("::")
    def scope_(fn, state: State) -> list[EisenInstance]:
        node = nodes.ModuleScope(state)
        return [node.get_end_instance()]

    @Visitor.for_asls(":", "var", "var?", "let", "val")
    def alloc_(fn, state: State) -> list[EisenInstance]:
        node = nodes.Decl(state)
        type = state.get_returned_type()
        return [InstanceVisitor.create_instance_inside_context(name, type, state)
            for name in node.get_names()]

    @Visitor.for_asls("ilet", "ivar")
    def iletivar_(fn, state: State) -> list[EisenInstance]:
        fn.apply(state.but_with_second_child())
        node = nodes.IletIvar(state)
        names = node.get_names()
        type = state.get_returned_type()
        componentwise_types = type.components if type.is_tuple() else [type]
        return [InstanceVisitor.create_instance_inside_context(name, type, state)
            for name, type in zip(names, componentwise_types)]

    @Visitor.for_asls("if")
    def if_(fn, state: State) -> Type:
        nodes.If(state).enter_context_and_apply(fn)
        return []

    @Visitor.for_asls("while")
    def while_(fn, state: State) -> Type:
        nodes.While(state).enter_context_and_apply(fn)
        return []

    @Visitor.for_asls("def", "create", ":=", "is_fn")
    def fn(fn, state: State) -> Type:
        nodes.CommonFunction(state).enter_context_and_apply(fn)
        return []

    @Visitor.for_asls("struct")
    def struct(fn, state: State) -> Type:
        node = nodes.Struct(state)
        if node.has_create_asl():
            fn.apply(state.but_with(asl=node.get_create_asl()))

    @Visitor.for_asls("call", "is_call")
    def raw_call(fn, state: State) -> Type:
        params_type = state.but_with_second_child().get_returned_type()
        fn.apply(state.but_with(asl=state.first_child(), arg_type=params_type))
        fn.apply(state.but_with_second_child())

        node = nodes.RefLike(state.but_with_first_child())
        return [node.resolve_function_instance(params_type)]
