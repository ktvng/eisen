from __future__ import annotations

from seer._params import Params

class ExceptionsHandler():
    def apply(cls, params: Params):
        for e in params.exceptions:
            print(e.to_str_with_context(params.txt))
        
        if params.exceptions:
            exit()