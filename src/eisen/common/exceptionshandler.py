from __future__ import annotations

from eisen.common.state import State

class ExceptionsHandler():
    def apply(cls, state: State):
        for e in state.exceptions:
            if state.print_to_watcher:
                state.watcher.write(e.to_str_with_context(state.txt))
            else:
                print(e.to_str_with_context(state.txt))

        return state.exceptions
