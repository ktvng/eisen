from __future__ import annotations

from eisen.common.params import State

class ExceptionsHandler():
    def apply(cls, params: State):
        for e in params.exceptions:
            print(e.to_str_with_context(params.txt))
        
        if params.exceptions:
            exit()