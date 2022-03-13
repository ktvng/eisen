from __future__ import annotations
from asyncio import start_unix_server

from alpaca.config import Config
from alpaca.asts import CLRList

class Indexer():
    class _Procedure():
        def __init__(self, f : Typing.Any, for_types : list[str]):
            self.f = f
            self.for_types = for_types
        
        def handles(self, type_name : str):
            return type_name in self.for_types

    class _Initializer():
        def __init__(self, f : Typing.Any):
            self.f = f

        def __call__(self, *args, **kwargs):
            return self.f(*args, **kwargs)

    class Params():
        def __init__(self, 
                config : Config, 
                asl : CLRList, 
                mod : AbstractModule, 
                fns : Typing.Any,
                struct_name: str):

            self.config = config
            self.asl = asl
            self.mod = mod
            self.fns = fns
            self.struct_name = struct_name

        def but_with(self,
                config: Config = None,
                asl: CLRList = None,
                mod: AbstractModule = None,
                fns: Typing.Any = None,
                struct_name: str = None) -> Indexer.Params:

            return Indexer.Params(
                config = self.config if config is None else config,
                asl = self.asl if asl is None else asl,
                mod = self.mod if mod is None else mod,
                fns = self.fns if fns is None else fns,
                struct_name= self.struct_name if struct_name is None else struct_name,
                )

    # args and kwargs used are the same as the initializer method decorated by
    # @initialize_by
    @classmethod
    def run(cls, fns : Typing.Any, *args, **kwargs):
        initializer = cls._get_initializer(fns)
        params = initializer(*args, **kwargs)
        Indexer.index(params)

    @classmethod
    def for_these_types(cls, names : list[str] | str):
        if isinstance(names, str):
            names = [names]
        def decorator(f):
            return Indexer._Procedure(f, names)
        return decorator

    @classmethod
    def initialize_by(cls, f):
        return Indexer._Initializer(f)

    @classmethod
    def _get_initializer(cls, obj_containing_fns : Typing.Any):
        attrs = dir(obj_containing_fns)
        fns = [getattr(obj_containing_fns, k) for k in attrs 
            if isinstance(getattr(obj_containing_fns, k), Indexer._Initializer)]

        if not fns:
            raise Exception("Cannot find initializer")
        if len(fns) > 1:
            raise Exception("Multiple initiators found; only one expected")
        
        return fns[0]

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
