from __future__ import annotations

from alpaca.concepts import Module, Context, TypeFactory, Type, AbstractParams, AbstractException
from alpaca.config import Config
from alpaca.clr import CLRList

from eisen.common.eiseninstance import EisenInstance
from eisen.state.basestate import BaseState, SharedBool
from eisen.validation.lookupmanager import LookupManager


class FunctionVisitorState(BaseState):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    def but_with(self,
            asl: CLRList = None,
            context: Context = None,
            mod: Module = None,
            inside_constructor: bool = None,
            struct_name: str = None
            ) -> BaseState:

        return self._but_with(
            asl=asl,
            context=context,
            mod=mod,
            inside_constructor=inside_constructor,
            struct_name=struct_name,)

    @classmethod
    def create_from_basestate(cls, state: BaseState):
        return FunctionVisitorState(**state._get(), struct_name="")

    def get_struct_name(self) -> str:
        """canonical way to access the name of the struct, if applicable"""
        return self.struct_name

    def get_variant_name(self) -> str:
        return self.struct_name

    def add_function_instance_to_module(self, instance: EisenInstance):
        self.get_enclosing_module().add_function_instance(instance)
