from __future__ import annotations

from typing import Callable
from alpaca.concepts import Module, Context, Type
from alpaca.clr import AST

from eisen.common.binding import BindingCondition, Binding
from eisen.state.basestate import BaseState
from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor

class BindingCheckerState(State_PostInstanceVisitor):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    def but_with(self,
            ast: AST = None,
            context: Context = None,
            mod: Module = None,
            inside_constructor: bool = None,
            binding_condition_producer: Callable[[str, Type], BindingCondition] = None,
            ) -> BindingCheckerState:

        return self._but_with(
            ast=ast,
            context=context,
            mod=mod,
            inside_constructor=inside_constructor,
            binding_condition_producer=binding_condition_producer)

    @staticmethod
    def create_from_basestate(state: BaseState) -> BindingCheckerState:
        return BindingCheckerState(**state._get(),
                                   inside_constructor=False,
                                   binding_condition_producer=None,
                                   )


    def is_inside_constructor(self) -> bool:
        """
        Returns true if the current state occurs inside a constructor.
        """
        return self.inside_constructor


    def add_binding_condition(self, condition: BindingCondition):
        """
        Adds the provided [condition] to the current context, indexed by its name.
        """
        self.get_context().add_obj("binding_condition", condition.name, condition)


    def get_binding_condition(self, name: str) -> BindingCondition:
        """
        Returns a the BindingCondition accessible from the current context under the provided [name]
        """
        return self.get_context().get_obj("binding_condition", name)


    def get_binding_condition_producer(self) -> Callable[[str, Type], BindingCondition]:
        """
        Returns a function which produces a BindingCondition.
        """
        return self.binding_condition_producer


    def get_all_local_binding_conditions(self) -> list[BindingCondition]:
        """
        Returns all BindingConditions which exist in the local context (does not resolve up the
        nested contexts).
        """
        return self.get_context().get_all_local_objs("binding_condition")


    def get_returned_bindings(self) -> list[Binding]:
        """
        Get the component-wise bindings of each type returned from this AST.
        """
        return [t.modifier for t in self.get_returned_type().unpack_into_parts()]
