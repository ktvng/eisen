from __future__ import annotations
from typing import TYPE_CHECKING

from alpaca.utils import Visitor
import eisen.adapters as adapters
from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor
from eisen.state.memcheckstate import MemcheckState
State = State_PostInstanceVisitor

if TYPE_CHECKING:
    from eisen.memory.memcheck import GetDeps

State = MemcheckState

class PossibleParamNamesVisitor(Visitor):
    def __init__(self, get_deps: GetDeps, debug: bool = False):
        self.get_deps = get_deps
        super().__init__(debug)

    def apply(self, state: State) -> list[list[str]]:
        return self._route(state.get_asl(), state)

    @Visitor.for_asls("call")
    def call_(fn, state: State):
        node = adapters.Call(state)
        possible_param_names = [fn.apply(state.but_with(asl=param))[0]
            for param in node.get_params()]

        f_deps = fn.get_deps.of_function(state.but_with(asl=node.get_fn_asl()))
        return f_deps.apply_to_parameter_names(possible_param_names)

    @Visitor.for_asls("ref")
    def ref_(fn, state: State):
        return [[adapters.Ref(state).get_name()]]

    # TODO: is this correct?
    @Visitor.for_asls("fn", ".")
    def fn_(fn, state: State):
        return [[]]

    @Visitor.for_asls("cast")
    def cast_(fn, state: State):
        return fn.apply(state.but_with_first_child())

    @Visitor.for_tokens
    def tokens_(fn, state: State):
        return [[]]

    @Visitor.for_default
    def default_(fn, state: State):
        print(state.asl, "arg_name resolver not implemented")
        exit()
