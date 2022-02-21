from __future__ import annotations
from functools import reduce
from typing import Union, List
import re

class CLRToken:
    def __init__(self, type : str, value : str):
        self.type = type
        self.value = value
        self.line_number = 0

    def __str__(self):
        # TODO: formalize this hack
        if self.type == "TAG":
            return self.value
        else:
            return self.type

class CLRList:
    def __init__(self, type : str, lst : list[CLRList | CLRToken]):
        self.type = type
        self._list = lst
        self.line_number = 0

    def __getitem__(self, key : int) -> CLRList | CLRToken:
        return self._list[key]

    def __setitem__(self, key : int, value : CLRList | CLRToken):
        self._list[key] = value

    def __delitem__(self, key : int):
        self._list.__delitem__[key]

    def __getslice__(self, i : int, j : int):
        return self._list[i, j]

    def __setslice__(self, *args, **kwargs):
        return self._list.__setslice__(args, kwargs)

    def __delslice__(self, *args, **kwargs):
        return self._list.__delslice__(args, kwargs)

    def __str__(self) -> str:
        str_reps = [str(x) for x in self._list]

        if any([("\n" in s) for s in str_reps]):
            parts = reduce(lambda lst, s: lst + s.split('\n'), str_reps, [])
            parts = [CLRList.indent + s for s in parts]
            parts_str = "\n".join(parts)
            return f"({self.type}\n{parts_str})"
        
        else:
            total_len = reduce(lambda sum, s: sum + len(s), str_reps, 0)
            if total_len < 64:
                parts_str = " ".join(str_reps)
                return f"({self.type} {parts_str})"
            else:
                parts = [CLRList.indent + s for s in str_reps]
                parts_str = "\n".join(parts)
                return f"({self.type}\n{parts_str})"

    def __iter__(self):
        return self._list.__iter__()

    indent = "  "

        
    
CLRRawList = List[Union[CLRList, CLRToken]]