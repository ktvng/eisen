from __future__ import annotations

from alpaca.validator import AbstractParams, AbstractException
from alpaca.concepts import Context
from alpaca.config import Config
from alpaca.asts import CLRList

class Params(AbstractParams):
    def __init__(self, 
            config: Config, 
            asl: CLRList, 
            txt: str,
            mod: Context,
            starting_mod: Context,
            struct_name: str,
            exceptions: list[AbstractException],
            is_ptr: bool,
            ):

        self.config = config
        self.asl = asl
        self.txt = txt
        self.mod = mod
        self.struct_name = struct_name
        self.starting_mod = starting_mod
        self.exceptions = exceptions
        self.is_ptr = is_ptr

    def but_with(self,
            config: Config = None,
            asl: CLRList = None,
            txt: str = None,
            mod: Context = None,
            starting_mod: Config = None,
            struct_name: str = None,
            exceptions: list[AbstractException] = None,
            is_ptr: bool = None,
            ):

        return self._but_with(config=config, asl=asl, txt=txt, mod=mod, starting_mod=starting_mod,
            struct_name=struct_name, exceptions=exceptions, is_ptr=is_ptr)

    def report_exception(self, e: AbstractException):
        self.exceptions.append(e)

    def __str__(self) -> str:
        return self.asl.type
