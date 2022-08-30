from __future__ import annotations
from curses import pair_content

from alpaca.config import Config
from alpaca.asts import CLRList
from alpaca.validator._abstracts import AbstractModule
from alpaca.utils._transform import _TransformFunction, PartialTransform, TransformFunction2

class Indexer2(TransformFunction2):
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
            return self._apply(
                match_args=[params.asl.type], 
                fn_args=[params])
        except:
            return None
