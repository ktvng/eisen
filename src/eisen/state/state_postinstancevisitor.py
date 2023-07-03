from __future__ import annotations


from eisen.common.eiseninstance import EisenInstance
from eisen.state.state_posttypecheck import State_PostTypeCheck
from eisen.state.basestate import BaseState

class State_PostInstanceVisitor(State_PostTypeCheck):
    """
    After the InstanceVisitor is run, certain nodes will have data about what EisenInstance is
    returned after executing the ASL at that state. This information is now available here.
    """

    @staticmethod
    def create_from_basestate(state: BaseState):
        return State_PostInstanceVisitor(**state._get())

    def get_instances(self) -> list[EisenInstance]:
        """
        Get the list of instances which would be returned by executing the current ASL.

        :return: The list of instances.
        :rtype: list[EisenInstance]
        """
        return self.get_node_data().instances
