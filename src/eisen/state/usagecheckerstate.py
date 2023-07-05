from __future__ import annotations

from alpaca.concepts import Module, Context
from alpaca.clr import AST

from eisen.state.basestate import BaseState
from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor
from eisen.common.usagestatus import UsageStatus

class UsageCheckerState(State_PostInstanceVisitor):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    def but_with(self,
            ast: AST = None,
            context: Context = None,
            mod: Module = None,
            inside_constructor: bool = None,
            exceptions: list = None,
            ) -> UsageCheckerState:

        return self._but_with(
            ast=ast,
            context=context,
            mod=mod,
            inside_constructor=inside_constructor,
            exceptions=exceptions)

    @staticmethod
    def create_from_basestate(state: BaseState) -> UsageCheckerState:
        """
        Create a new instance of NilCheckState from any descendant of BaseState

        :param state: The BaseState instance
        :type state: BaseState
        :return: A instance of NilCheckState
        :rtype: NilCheckState
        """
        return UsageCheckerState(**state._get(), inside_constructor=False)


    def is_inside_constructor(self) -> bool:
        """
        Returns whether or not the current State occurs inside a constructor.

        :return: True if this state occurs inside a constructor.
        :rtype: bool
        """
        return self.inside_constructor

    def add_usagestatus(self, inst: UsageStatus):
        self.get_context().add_instancestate(inst)

    def get_usagestatus(self, name: str) -> UsageStatus:
        return self.get_context().get_instancestate(name)
