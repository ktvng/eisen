from __future__ import annotations

from eisen.common.state import State

class ExceptionsHandler():
    def apply(cls, state: State):
        for e in state.exceptions:
            print(e.to_str_with_context(state.txt))
        
        if state.exceptions:
            exit()