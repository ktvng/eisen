from __future__ import annotations

from alpaca.concepts import Module, Context
from alpaca.clr import CLRList

from eisen.state.basestate import BaseState
from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor
from eisen.validation.nilablestatus import NilableStatus

class RestrictionVisitorState(State_PostInstanceVisitor):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    def but_with(self,
            asl: CLRList = None,
            context: Context = None,
            mod: Module = None,
            inside_constructor: bool = None,
            left_of_assign: bool = None,
            exceptions: list = None,
            ) -> RestrictionVisitorState:

        return self._but_with(
            asl=asl,
            context=context,
            mod=mod,
            inside_constructor=inside_constructor,
            left_of_assign=left_of_assign,
            exceptions=exceptions)

    @classmethod
    def create_from_basestate(cls, state: BaseState) -> RestrictionVisitorState:
        """
        Create a new instance of NilCheckState from any descendant of BaseState

        :param state: The BaseState instance
        :type state: BaseState
        :return: A instance of NilCheckState
        :rtype: NilCheckState
        """
        return RestrictionVisitorState(**state._get(), inside_constructor=False,
                                       left_of_assign=False)


    def is_inside_constructor(self) -> bool:
        """
        Returns whether or not the current State occurs inside a constructor.

        :return: True if this state occurs inside a constructor.
        :rtype: bool
        """
        return self.inside_constructor

    def is_left_of_assignment_operator(self) -> bool:
        return self.left_of_assign
