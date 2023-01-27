from __future__ import annotations

from eisen.state.basestate import BaseState

class ExceptionsHandler():
    def apply(cls, state: BaseState):
        for e in state.exceptions:
            if state.print_to_watcher:
                state.watcher.write(e.to_str_with_context(state.txt))
            else:
                print(e.to_str_with_context(state.txt))

        return state.exceptions
