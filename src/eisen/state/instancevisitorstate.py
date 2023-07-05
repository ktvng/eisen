from __future__ import annotations

from alpaca.concepts import Module, Context, Type
from alpaca.clr import AST

from eisen.state.basestate import BaseState
from eisen.state.state_posttypecheck import State_PostTypeCheck as State

class InstanceVisitorState(State):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    def but_with(self,
            ast: AST = None,
            context: Context = None,
            mod: Module = None,
            arg_type: Type = None,
            is_ptr: bool = None,
            ) -> InstanceVisitorState:

        return self._but_with(
            ast=ast,
            context=context,
            mod=mod,
            arg_type=arg_type,
            is_ptr=is_ptr,)

    @classmethod
    def create_from_basestate(cls, state: BaseState):
        return InstanceVisitorState(**state._get(),
            arg_type=None,
            is_ptr=None,)

    def get_returned_type(self) -> Type:
        """canonical way to access the type returned from this node"""
        return self.get_node_data().returned_type

    def get_arg_type(self) -> Type | None:
        return self.arg_type
