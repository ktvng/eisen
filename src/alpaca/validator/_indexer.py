from __future__ import annotations

from alpaca.config import Config
from alpaca.asts import CLRList
from alpaca.validator._abstracts import AbstractModule

class Indexer():
    class _Procedure():
        def __init__(self, f, for_types : list[str]):
            self.f = f
            self.for_types = for_types
        
        def handles(self, type_name : str):
            return type_name in self.for_types

    @classmethod
    def for_these_types(cls, names : list[str] | str):
        if isinstance(names, str):
            names = [names]
        def decorator(f):
            return Indexer._Procedure(f, names)
        return decorator

    @classmethod
    def _get_matching_procedure(cls, type_name: str, params: Indexer.Params) -> Indexer._Procedure:
        obj_containing_fns = params.fns
        attrs = dir(obj_containing_fns)
        fns = [getattr(obj_containing_fns, k) for k in attrs 
            if isinstance(getattr(obj_containing_fns, k), Indexer._Procedure)]
        matching_fn = [f for f in fns if f.handles(type_name)]

        if len(matching_fn) == 0:
            return None
        if len(matching_fn) > 1:
            raise Exception(f"Multiple procedures for'{type_name}'; only one expected")

        return matching_fn[0] 

    @classmethod
    def index(cls, params : Indexer.Params) -> None:
        proc = cls._get_matching_procedure(params.asl.type, params)
        if proc:
            proc.f(params)
