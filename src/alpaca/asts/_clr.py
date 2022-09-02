from __future__ import annotations
from functools import reduce
from typing import Union, List

from error import Raise

class CLRToken:
    def __init__(self, type : str, value : str, line_number : int):
        self.type = type
        self.value = value
        self.line_number = line_number

    def __str__(self):
        # TODO: formalize this hack
        if self.type == "TAG" or self.type == "int" or self.type == "bool":
            return self.value
        elif self.type == "str":
            return f'{self.value}'
        else:
            return + self.type

class CLRList:
    def __init__(self, type : str, lst : list[CLRList | CLRToken], line_number = 0):
        self.type = type
        self._list = lst
        self.line_number = line_number
        self.data = None
        self.module = None
        self.returns_type = None

    def first(self) -> CLRList | CLRToken:
        if not self._list:
            raise Exception("list is empty; first does not exist")

        return self._list[0]

    def second(self) -> CLRList | CLRToken:
        if len(self._list) < 2:
            raise Exception("list is less than size 2; second does not exist")

        return self._list[1]

    def third(self) -> CLRList | CLRToken:
        if len(self._list) < 3:
            raise Exception("list is less than size 3; second does not exist")

        return self._list[2]

    def head(self) -> CLRList | CLRToken:
        if not self._list:
            raise Exception("list is empty; head does not exist")

        return self._list[0]

    # The head of a CLRList is the first element; if that element is a token, then
    # head_value will return the value of that CLRToken
    def head_value(self) -> str:
        if not isinstance(self._list[0], CLRToken):
            raise Exception(
                f"expected first element of CLRList to be a CLRToken. Got:\n {str(self)}")
        
        return self._list[0].value

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

    def __len__(self) -> int:
        return len(self._list)

    def __str__(self) -> str:
        str_reps = [str(x) for x in self._list]

        if any([("\n" in s) for s in str_reps]):
            parts = reduce(lambda lst, s: lst + s.split('\n'), str_reps, [])
            parts = [CLRList.indent + s for s in parts]
            parts_str = "\n".join(parts)
            if parts_str.strip()[0] != "(":
                parts_str = parts_str.strip()
                return f"({self.type} {parts_str})"

            return f"({self.type}\n{parts_str})"
        
        else:
            total_len = reduce(lambda sum, s: sum + len(s.strip()), str_reps, 0)
            if total_len < 64:
                parts_str = " ".join(str_reps)
                return f"({self.type} {parts_str})"
            else:
                parts = [CLRList.indent + s for s in str_reps]
                parts_str = "\n".join(parts)
                if parts_str.strip()[0] != "(":
                    parts_str = parts_str.strip()
                    return f"({self.type} {parts_str})"

                return f"({self.type}\n{parts_str})"

    def __iter__(self):
        return self._list.__iter__()

    indent = "  "

        
    
CLRRawList = List[Union[CLRList, CLRToken]]