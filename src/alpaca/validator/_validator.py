from __future__ import annotations

from alpaca.config import Config
from alpaca.asts import CLRList, CLRToken
from alpaca.validator._abstracts import AbstractModule, AbstractException
from alpaca.utils._transform import PartialTransform, TransformFunction2

class Validator2(TransformFunction2):
    def __init__(self):
        super().__init__()
        self.exceptions = []

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
            print(e)
            return None

    def report_exception(self, e: AbstractException):
        self.exceptions.append(e)

    def print_exceptions(self, params):
        for e in self.exceptions:
            print(e.to_str_with_context(params.txt)) 


class Validator():
    @classmethod
    def for_these_types(cls, matching_names: list[str] | str):
        if isinstance(matching_names, str):
            matching_names = [matching_names]
        def decorator(f):
            predicate = lambda n: n in matching_names
            return PartialTransform(predicate, f)

        return decorator 

    exceptions: list[AbstractException] = []

    @classmethod
    def report_exception(cls, e: AbstractException):
        cls.exceptions.append(e)

    @classmethod
    def validate(cls, params : Validator.Params):
        if isinstance(params.asl, CLRToken):
            return params.mod.resolve_type_by(name=params.asl.type)
        return params.fn.apply([params.asl.type], [params])

    @classmethod
    def run(cls, params):
        cls.exceptions.clear()
        Validator.validate(params)

        for e in cls.exceptions:
            print(e.to_str_with_context(params.txt))
            # return None
        return params.mod

    class Params:
        def __init__(self, config: Config, asl: CLRList, txt: str, mod: AbstractModule, fn):
            self.config = config
            self.asl = asl
            self.txt = txt
            self.mod = mod
            self.fn = fn

        def but_with(self, *args, **kwargs):
            pass
