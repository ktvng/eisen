from __future__ import annotations

from alpaca.concepts import Module, Context
from alpaca.clr import AST

from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor
from eisen.state.basestate import BaseState
from eisen.validation.nilablestatus import NilableStatus

class NilCheckState(State_PostInstanceVisitor):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    def but_with(self,
            ast: AST = None,
            context: Context = None,
            mod: Module = None,
            inside_cond: bool = None,
            inside_and_domain: bool = None,
            exceptions: list = None,
            changed_nilstates: set[NilableStatus] = None
            ) -> NilCheckState:

        return self._but_with(
            ast=ast,
            context=context,
            mod=mod,
            inside_cond=inside_cond,
            inside_and_domain=inside_and_domain,
            exceptions=exceptions,
            changed_nilstates=changed_nilstates)

    @classmethod
    def create_from_basestate(cls, state: BaseState) -> NilCheckState:
        """
        Create a new instance of NilCheckState from any descendant of BaseState

        :param state: The BaseState instance
        :type state: BaseState
        :return: A instance of NilCheckState
        :rtype: NilCheckState
        """
        return NilCheckState(**state._get(), inside_cond=False, inside_and_domain=True, changed_nilstates=set())

    def is_inside_cond(self) -> bool:
        """
        Returns whether or not the current state occurs inside a (cond ...)
        list.

        Because if-statements (which are built from conds) are used to handle
        nil state, and may be used to handle the case where a variable is nil,
        (even assigning it to some default value so it is not nil), the NilCheck
        must be more intelligent around if-statements and (cond... ) lists

        The NilCheck will change this bool value to true when parsing a (cond ...)
        list, and this will be passed recursively to all internal lists.

        :return: True if the current state occurs inside a (cond ...) list
        :rtype: bool
        """
        return self.inside_cond

    def is_inside_and_domain(self) -> bool:
        """
        TODO

        :return: _description_
        :rtype: bool
        """
        return self.inside_and_domain

    def get_nilstatus(self, name: str) -> NilableStatus:
        """
        Return the NilableStatus for a local variable, looked up by name

        :param name: The name of the local variable.
        :type name: str
        :return: The NilableStatus of the local variable.
        :rtype: NilableStatus
        """
        return self.get_context().get_nilstatus(name)

    def add_nilstatus(self, nilstate: NilableStatus) -> None:
        """
        Add a NilableStatus for some local variable to the local context. This may
        supercede the parent context. This means that a given local variable may have
        two NilableStates (one stored in the parent context, and one stored in the
        local context).

        But based on the resolution rules, the NilableStatus of the most local context
        is preferred.

        :param nilstate: The NilableStatus to add
        :type nilstate: NilableStatus
        """
        self.get_context().add_nilstatus(nilstate.name, nilstate)

    def try_update_nilstatus(self, name: str, update_with: NilableStatus):
        """
        Try to update the NilableStatus which is already added to some context. This
        will have no effect if there is no NilableStatus for 'name' stored already

        Note: This not modify the existing NilableStatus, but create a new instance
        with the updated information. Further, as the existing NilableStatus for
        the variable may exist in a parent context, the new, updated NilableStatus
        may not even replace the existing--it will be added to the current context,
        which is not guaranteed to be the same context that the existing NilableStatus
        was found in

        :param name: The name of the variable who's status should be updated
        :type name: str
        :param update_with: The NilableStatus who's state will be used to create a new,
        updated NilableStatus.
        :type update_with: NilableStatus
        """
        # this may get the nilstate from the parent context, and add it to the
        # current (child) context. This is desired
        existing = self.get_nilstatus(name)
        if existing:
            self.mark_status_as_changed(existing)
            self.get_context().add_nilstatus(name, existing.update(update_with))

    def get_changed_nilstatus_names(self) -> set[NilableStatus]:
        """
        Return a list of NilableStatuses which have been changed in the current
        context.

        Because each Context adds its own version of a variables NilableStatus,
        after a child context has finished, any changes to the NilableStatus of a
        variable may only be reflected in the child context, not the parent.

        This method returns a list of all NilableStatus which may need to be updated
        in the parent context.

        :return: The list of changed NilableStatus from the current context.
        :rtype: list[NilableStatus]
        """
        return self.changed_nilstates

    def mark_status_as_changed(self, status: NilableStatus):
        """
        Mark 'status' as having change in the local context.

        :param status: The status to mark as changed.
        :type status: NilableStatus
        """
        self.changed_nilstates.add(status)
