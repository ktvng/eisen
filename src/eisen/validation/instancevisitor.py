from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.concepts import Type

from eisen.validation.nodetypes import Nodes
from eisen.common.state import State
from eisen.common.eiseninstance import EisenInstance

class InstanceVisitor(Visitor):
    """creates and persists instances for terminal asls"""

    def apply(self, state: State) -> list[EisenInstance]:
        result: list[EisenInstance] = self._route(state.get_asl(), state)
        if result:
            state.set_instances(result)
        return result

    @classmethod
    def create_instance_inside_context(cls, name: str, type: Type, state: State):
        """add a new instance to the current context and return it."""
        instance = EisenInstance(
            name=name,
            type=type,
            context=state.get_context(),
            asl=state.get_asl(),
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
        Nodes.Mod(state).enter_module_and_apply_fn_to_child_asls(fn)
        return []

    @Visitor.for_asls("ref")
    def ref_(fn, state: State) -> list[EisenInstance]:
        return [Nodes.Ref(state).resolve_instance()]

    @Visitor.for_asls("::")
    def scope_(fn, state: State) -> list[EisenInstance]:
        node = Nodes.ModuleScope(state)
        return [node.get_end_instance()]

    @Visitor.for_asls(":")
    def colon_(fn, state: State) -> list[EisenInstance]:
        node = Nodes.Colon(state)
        type = state.get_returned_type()
        return [InstanceVisitor.create_instance_inside_context(name, type, state)
            for name in node.get_names()]

    @Visitor.for_asls("var", "var?", "let", "val")
    def alloc_(fn, state: State) -> list[EisenInstance]:
        node = Nodes.LetVarVal(state)
        type = state.get_returned_type()
        return [InstanceVisitor.create_instance_inside_context(name, type, state)
            for name in node.get_names()]

    @Visitor.for_asls("ilet", "ivar")
    def iletivar_(fn, state: State) -> list[EisenInstance]:
        fn.apply(state.but_with_second_child())
        node = Nodes.IletIvar(state)
        names = node.get_names()
        type_to_be_assigned = state.get_returned_type()
        componentwise_types = node.unpack_assigned_types(type_to_be_assigned)
        return [InstanceVisitor.create_instance_inside_context(name, type, state)
            for name, type in zip(names, componentwise_types)]

    @Visitor.for_asls("if")
    def if_(fn, state: State) -> Type:
        for child in state.get_child_asls():
            fn.apply(state.but_with(
                asl=child, 
                context=state.create_block_context("if")))
        return []

    @Visitor.for_asls("while")
    def while_(fn, state: State) -> Type:
        fn.apply(state.but_with(
            asl=state.first_child(),
            context=state.create_block_context("while"))) 
        return []

    @Visitor.for_asls("def", "create", ":=", "is_fn")
    def fn(fn, state: State) -> Type:
        Nodes.CommonFunction(state).enter_context_and_apply_fn(fn)
        return []

    @Visitor.for_asls("struct")
    def struct(fn, state: State) -> Type:
        node = Nodes.Struct(state)
        if node.has_create_asl():
            fn.apply(state.but_with(asl=node.get_create_asl()))
    
    @Visitor.for_asls("call")
    def raw_call(fn, state: State) -> Type:
        params_type = state.but_with_second_child().get_returned_type()
        fn.apply(state.but_with(asl=state.first_child(), arg_type=params_type))
        fn.apply(state.but_with_second_child())
        return []