from __future__ import annotations

from alpaca.config import Config
from alpaca.asts import CLRList, CLRToken
from alpaca.validator._abstracts import AbstractModule, AbstractException
from alpaca.validator._indexer import Indexer

class Validator():
    class _Procedure():
        def __init__(self, f, handles: list[str]):
            self.f = f
            self._handles = handles

        def handles(self, type : str):
            return type in self._handles

    class Params:
        def __init__(self, config: Config, asl: CLRList, txt: str, mod: AbstractModule, exceptions: list[AbstractException], fns):
            self.config = config
            self.asl = asl
            self.txt = txt
            self.mod = mod
            self.fns = fns
            self.exceptions = exceptions

        def but_with(self, *args, **kwargs):
            pass

    @classmethod
    def for_these_types(cls, names : list[str] | str):
        if isinstance(names, str):
            names = [names]

        def decorator(f):
            return Validator._Procedure(f, names)

        return decorator

    @classmethod
    def run(cls, params):
        Indexer.index(params)
        Validator.validate(params)


        # exceptions : list[AbstractException] = []
        # global_mod = AbstractModule("global")
        # Indexer.run(fns, config, asl, global_mod)
        # params = Validator._get_init_params_fn(fns)
        # Validator.validate(params)

        for e in params.exceptions:
            print(e.to_str_with_context(params.txt))
            # return None

        return params.mod

    @classmethod
    def _get_init_params_fn(cls, fns):
        attrs = dir(fns)
        fns = [getattr(fns, k) for k in attrs 
            if isinstance(getattr(fns, k), Validator._Inits)]
        if not fns:
            raise Exception(f"Validation expects at least one method decorated with @Validator.inits_params")
        if len(fns) > 1:
            raise Exception(f"Validation expects at only one method decorated with @Validator.inits_params")

        return fns[0].f


    @classmethod
    def _get_matching_procedure_for_type(cls, fns, type_name : str):
        attrs = dir(fns)
        fns = [getattr(fns, k) for k in attrs 
            if isinstance(getattr(fns, k), Validator._Procedure)]
        matching_fn = [f for f in fns if f.handles(type_name)]
        
        if not matching_fn:
            raise Exception(f"Validation could not match type '{type_name}")
        if len(matching_fn) > 1:
            raise Exception(f"Validation encountered more than one match for '{type_name}'; expected only one")

        return matching_fn[0].f

    @classmethod
    def validate(cls, params : Validator.Params):
        if isinstance(params.asl, CLRToken):
            return params.mod.resolve_type_by(name=params.asl.type)

        f = cls._get_matching_procedure_for_type(params.fns, params.asl.type)
        return f(params)
 