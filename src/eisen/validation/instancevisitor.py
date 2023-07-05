from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.concepts import Type

import eisen.adapters as adapters
from eisen.common.eiseninstance import EisenInstance
from eisen.state.state_posttypecheck import State_PostTypeCheck
from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor
from eisen.state.instancevisitorstate import InstanceVisitorState

State = InstanceVisitorState

class InstanceVisitor(Visitor):
    """creates and persists instances for terminal asts"""

    def run(self, state: State_PostTypeCheck):
        self.apply(InstanceVisitorState.create_from_basestate(state))
        return State_PostInstanceVisitor.create_from_basestate(state)

    def apply(self, state: State) -> list[EisenInstance]:
        result: list[EisenInstance] = self._route(state.get_ast(), state)
        if result:
            state.get_node_data().instances = result
        return result

    @classmethod
    def create_instance_inside_context(cls, name: str, type: Type, state: State,
            is_function: bool=False):
        """add a new instance to the current context and return it."""
        instance = EisenInstance(
            name=name,
            type=type,
            context=state.get_context(),
            ast=state.get_ast(),
            # TODO: fix this abuse of as_ptr
            is_ptr=state.is_ptr,
            is_function=is_function)
        state.get_context().add_instance(instance)
        return instance

    @Visitor.for_tokens
    def token_(fn, state: State) -> list[EisenInstance]:
        return []

    @Visitor.for_ast_types("interface")
    def no_action_(fn, state: State) -> list[EisenInstance]:
        return []

    @Visitor.for_default
    def continue_(fn, state: State) -> list[EisenInstance]:
        state.apply_fn_to_all_children(fn)
        return []

    @Visitor.for_ast_types("mod")
    def mod_(fn, state: State) -> list[EisenInstance]:
        adapters.Mod(state).enter_module_and_apply(fn)
        return []

    @Visitor.for_ast_types("ref", "fn")
    def ref_(fn, state: State) -> list[EisenInstance]:
        return [adapters.Ref(state).resolve_instance()]

    @Visitor.for_ast_types(*adapters.ArgsRets.ast_types)
    def rets_(fn, state: State) -> list[EisenInstance]:
        for child in state.get_child_asts():
            fn.apply(state.but_with(ast=child, is_ptr=True))
        return []

    @Visitor.for_ast_types("::")
    def scope_(fn, state: State) -> list[EisenInstance]:
        node = adapters.ModuleScope(state)
        return [node.get_end_instance()]

    @Visitor.for_ast_types(*adapters.Typing.ast_types)
    def alloc_(fn, state: State) -> list[EisenInstance]:
        node = adapters.Typing(state)
        type = state.get_returned_type()
        return [InstanceVisitor.create_instance_inside_context(
                name, type, state,
                is_function=type.is_function())
            for name in node.get_names()]

    @Visitor.for_ast_types(*adapters.InferenceAssign.ast_types)
    def iletivar_(fn, state: State) -> list[EisenInstance]:
        fn.apply(state.but_with_second_child())
        node = adapters.InferenceAssign(state)
        names = node.get_names()
        type = state.get_returned_type()
        componentwise_types = type.components if type.is_tuple() else [type]
        return [InstanceVisitor.create_instance_inside_context(
            name, type, state,
            is_function=type.is_function())
            for name, type in zip(names, componentwise_types)]

    @Visitor.for_ast_types("if")
    def if_(fn, state: State) -> Type:
        adapters.If(state).enter_context_and_apply(fn)
        return []

    @Visitor.for_ast_types("while")
    def while_(fn, state: State) -> Type:
        adapters.While(state).enter_context_and_apply(fn)
        return []

    @Visitor.for_ast_types("def", "create", ":=", "is_fn")
    def fn(fn, state: State) -> Type:
        adapters.CommonFunction(state).enter_context_and_apply(fn)
        return []

    @Visitor.for_ast_types("struct")
    def struct(fn, state: State) -> Type:
        node = adapters.Struct(state)
        if node.has_create_ast():
            fn.apply(state.but_with(ast=node.get_create_ast()))

    @Visitor.for_ast_types("call", "is_call")
    def raw_call(fn, state: State) -> Type:
        params_type = state.but_with_second_child().get_returned_type()
        fn.apply(state.but_with(ast=state.first_child(), arg_type=params_type))
        fn.apply(state.but_with_second_child())

        node = adapters.RefLike(state.but_with_first_child())
        return [node.resolve_function_instance(params_type)]
