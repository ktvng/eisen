from __future__ import annotations

from alpaca.concepts import Type

from eisen.common.restriction import GeneralRestriction
from eisen.state.basestate import BaseState

class State_PostTypeCheck(BaseState):
    """
    After the TypeChecker is run, it will be determined what Type is returned by evaluating each
    ASL. This is now an method available for use, in addition to obtaining any restrictions on that
    Type.
    """
    @classmethod
    def create_from_basestate(cls, state: BaseState):
        return State_PostTypeCheck(**state._get())


    def get_returned_type(self) -> Type:
        """
        For use after the TypeChecker is run, this will return the Type that results for evaluating
        the current State's ASL.

        E.g. (+ 4 5) will return 'int' as the (+ ...) ASL evaluates to the same type as both
        operands.

        :return: The type which would be returned by evaluating the ASL at this State.
        :rtype: Type
        """
        return self.get_node_data().returned_type


    def get_restriction(self) -> GeneralRestriction:
        """
        Get any restriction on the Type that results from evaluating the current State's ASL.

        :return: The restrictions of the returned Type.
        :rtype: GeneralRestriction
        """
        return self.get_returned_type().get_restrictions()[0]
