from __future__ import annotations

import traceback

from alpaca.config import Config
from alpaca.asts import CLRList, CLRToken
from alpaca.validator._abstracts import AbstractModule
from alpaca.utils._transform import PartialTransform, Wrangler

class Validator(Wrangler):
    def __init__(self):
        super().__init__()

    @classmethod
    def for_these_types(cls, names : list[str] | str):
        if isinstance(names, str):
            names = [names]
        def decorator(f):
            predicate = lambda n: n in names
            return PartialTransform(predicate, f)
        return decorator 

    def apply(self, params):
        try:
            if isinstance(params.asl, CLRToken):
                return params.mod.resolve_type_by(name=params.asl.type)
            return self._apply(
                match_args=[params.asl.type], 
                fn_args=[params])
        except Exception as e:
            traceback.print_exc()
            print(e)
            exit()
            return None

    class Params:
        def __init__(self, config: Config, asl: CLRList, txt: str, mod: AbstractModule, fn):
            self.config = config
            self.asl = asl
            self.txt = txt
            self.mod = mod
            self.fn = fn

        def but_with(self, *args, **kwargs):
            pass
