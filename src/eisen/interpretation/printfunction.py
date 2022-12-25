from __future__ import annotations

import re
from eisen.interpretation.obj import Obj

class PrintFunction():
    @classmethod
    def emulate(cls, redirect: str, *args: list[Obj]) -> str:
        base = args[0].value
        arg_strs = cls._convert_args_to_strs(args[1:])
        tag_regex = re.compile(r"%\w")
        for arg in arg_strs:
            base = tag_regex.sub(arg, base, count=1)
        if redirect is None:
            print(base)
        return base

    @classmethod
    def _convert_args_to_strs(cls, args: list[Obj]) -> list[str]:
        arg_strs = []
        for arg in args:
            if isinstance(arg.value, bool):
                arg_strs.append("true" if arg.value else "false")
            else:
                arg_strs.append(str(arg))
        return arg_strs
