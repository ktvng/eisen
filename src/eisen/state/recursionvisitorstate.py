from __future__ import annotations

from alpaca.concepts import Module, Context
from alpaca.clr import AST

from eisen.state.basestate import BaseState
from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor
from eisen.common.eiseninstance import FunctionInstance

class RecursionVisitorState(State_PostInstanceVisitor):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    def but_with(self,
            ast: AST = None,
            context: Context = None,
            mod: Module = None,
            checked_functions: set[FunctionInstance] = None,
            original_function: FunctionInstance = None,
            ) -> RecursionVisitorState:

        return self._but_with(
            ast=ast,
            context=context,
            mod=mod,
            checked_functions=checked_functions,
            original_function=original_function,
            )

    @classmethod
    def create_from_basestate(cls, state: BaseState):
        return RecursionVisitorState(**state._get(),
            checked_functions=None,
            original_function=None,
            )

    def mark_function_as_checked(self, instance: FunctionInstance):
        self.checked_functions.add(instance)

    def is_function_checked(self, instance: FunctionInstance) -> bool:
        return instance in self.checked_functions

    def is_this_the_original_instance(self, instance: FunctionInstance) -> bool:
        return instance == self.original_function
