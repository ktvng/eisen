from __future__ import annotations

from eisen.common.eiseninstance import EisenInstance
from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor
from eisen.state.basestate import BaseState
from eisen.memory.deps import FunctionDepsDatabase

class State_PostSpreadVisitor(State_PostInstanceVisitor):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    @staticmethod
    def create_from_basestate(state: BaseState, deps_db: FunctionDepsDatabase) -> State_PostSpreadVisitor:
        return State_PostSpreadVisitor(**state._get(), deps_db=deps_db)

    def get_deps_of_function(self, function_instance: EisenInstance):
        deps_db: FunctionDepsDatabase = self.deps_db
        return deps_db.lookup_deps_of(function_instance)
