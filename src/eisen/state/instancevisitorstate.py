from __future__ import annotations

from alpaca.concepts import Module, Context, Type
from alpaca.clr import CLRList

from eisen.state.statea import StateA

class InstanceVisitorState(StateA):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    def but_with(self,
            asl: CLRList = None,
            context: Context = None,
            mod: Module = None,
            inside_constructor: bool = None,
            arg_type: Type = None,
            is_ptr: bool = None,
            ) -> InstanceVisitorState:

        return self._but_with(
            asl=asl,
            context=context,
            mod=mod,
            inside_constructor=inside_constructor,
            arg_type=arg_type,
            is_ptr=is_ptr,)

    @classmethod
    def create_from_state_A(cls, state: StateA):
        return InstanceVisitorState(**state._get(),
            arg_type=None,
            is_ptr=None,)

    def get_returned_type(self) -> Type:
        """canonical way to access the type returned from this node"""
        return self.get_node_data().returned_type

    def get_arg_type(self) -> Type | None:
        return self.arg_type
