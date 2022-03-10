from __future__ import annotations

from alpaca.config import Config
from alpaca.asts import CLRList, CLRToken
from alpaca.validator._abstractmodule import AbstractModule
from alpaca.validator._indexer import Indexer

class Validator():
    class _Procedure():
        def __init__(self, f : Typing.Any, handles : list[str]):
            self.f = f
            self._handles = handles

        def handles(self, type : str):
            return type in self._handles

    class Params:
        attrs = ["config", "asl", "validator", "exceptions", "mod", "context", "flags"]

        def __init__(self, 
                config : Config, 
                asl : CLRList, 
                validatefunctions : Typing.Any,
                exceptions : list[Exceptions.AbstractException],
                mod : AbstractModule,
                context : Context,
                flags : str,
                ):

            self.config = config
            self.asl = asl
            self.functions = validatefunctions
            self.exceptions = exceptions
            self.mod = mod
            self.context = context
            self.flags = flags

        def has_flag(self, flag : str) -> bool:
            if self.flags is None:
                return False
            return flag in self.flags

        def derive_flags_including(self, flags : str) -> str:
            return self.flags + ";" + flags

        def but_with(self,
                config : Config = None,
                asl : CLRList = None,
                validatefunctions : Typing.Any = None,
                exceptions : list[Exceptions.AbstractException] = None,
                mod : AbstractModule = None,
                context : Context = None,
                flags : str = None,
                ):

            new_params = Validator.Params.new_from(self)
            if config is not None:
                new_params.config = config
            if asl is not None:
                new_params.asl = asl
            if validatefunctions is not None:
                new_params.functions = validatefunctions
            if exceptions is not None:
                new_params.exceptions = exceptions
            if mod is not None:
                new_params.mod = mod
            if context is not None:
                new_params.context = context
            if flags is not None:
                new_params.flags = flags
            
            return new_params

        @classmethod
        def new_from(cls, params : Validator.Params, overrides : dict = {}) -> Validator.Params:
            new_params = Validator.Params(
                params.config,
                params.asl,
                params.functions,
                params.exceptions,
                params.mod,
                params.context,
                params.flags,
                )

            for k, v in overrides:
                if k in Validator.Params.attrs:
                    setattr(new_params, k, v)
            
            return new_params

    @classmethod
    def for_these_types(cls, names : list[str] | str):
        if isinstance(names, str):
            names = [names]

        def decorator(f):
            return Validator._Procedure(f, names)

        return decorator

    @classmethod
    def run(cls, config : Config, asl : CLRList, fns : Typing.Any, txt : str):
        exceptions : list[Exceptions.AbstractException] = []
        global_mod = AbstractModule("global")
        Indexer.run(fns, config, asl, global_mod)
        vparams = Validator.Params(
            config, 
            asl, 
            fns, 
            exceptions, 
            global_mod, 
            global_mod.context, 
            "")

        Validator.validate(vparams)

        for e in exceptions:
            print(e.to_str_with_context(txt))

        return global_mod

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
            return params.mod.resolve_type_name(params.asl.type)

        f = cls._get_matching_procedure_for_type(params.functions, params.asl.type)
        return f(params)
 