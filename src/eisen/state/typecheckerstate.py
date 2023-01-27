from __future__ import annotations

from alpaca.concepts import Module, Context, TypeFactory, Type, AbstractParams, AbstractException
from alpaca.config import Config
from alpaca.clr import CLRList

from eisen.common.eiseninstance import EisenInstance
from eisen.state.basestate import BaseState, SharedBool
from eisen.validation.lookupmanager import LookupManager


class TypeCheckerState(BaseState):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    def but_with(self,
            asl: CLRList = None,
            context: Context = None,
            mod: Module = None,
            inside_constructor: bool = None,
            arg_type: Type = None
            ) -> BaseState:

        return self._but_with(
            asl=asl,
            context=context,
            mod=mod,
            inside_constructor=inside_constructor,
            arg_type=arg_type,)

    @classmethod
    def create_from_basestate(cls, state: BaseState):
        return TypeCheckerState(**state._get(), arg_type=None)

    def get_arg_type(self) -> Type | None:
        return self.arg_type
