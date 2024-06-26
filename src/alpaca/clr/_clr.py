from __future__ import annotations
from functools import reduce
from typing import Union, List
import uuid
from abc import ABC

class ASTElement(ABC):
    def is_ast(self) -> bool:
        return False

    def is_token(self) -> bool:
        return False


class ASTToken(ASTElement):
    def __init__(self, type_chain: list[str], value: str, line_number: int = 0):
        self.type = type_chain[0]
        self.type_chain = type_chain
        self.value = value
        self.line_number = line_number
        self.data = None

    def is_classified_as(self, type: str) -> bool:
        return type in self.type_chain

    def __str__(self):
        # TODO: formalize this hack
        if self.type == "TAG" or self.type == "int" or self.type == "bool" or self.type == "code":
            return self.value
        elif self.type == "str":
            return f'"{self.value}"'
        else:
            return self.type

    def is_token(self) -> bool:
        return True


class AST(ASTElement):
    indent = "  "

    def __init__(self, type : str, lst : list[AST | ASTToken], line_number = 0, guid: uuid.UUID = None, data = None):
        self.type = type
        self._list = lst
        self.line_number = line_number
        self.data = data
        if guid is None:
            self.guid = uuid.uuid4()
        else:
            self.guid = guid

    def is_ast(self) -> bool:
        return True

    def get_all_children(self) -> list[AST | ASTToken]:
        return self._list.copy()

    def has_no_children(self) -> bool:
        return len(self._list) == 0

    def first(self) -> AST | ASTToken:
        if not self._list:
            raise Exception(f"AST: first does not exist; len={len(self._list)}; self={self.type}")
        return self._list[0]

    def second(self) -> AST | ASTToken:
        if len(self._list) < 2:
            raise Exception(f"AST: second does not exist; len={len(self._list)}; self={self.type}")
        return self._list[1]

    def third(self) -> AST | ASTToken:
        if len(self._list) < 3:
            raise Exception(f"AST: third does not exist; len={len(self._list)}; self={self.type}")
        return self._list[2]

    def update(self, type: str, lst: list[AST | ASTToken] = None):
        self.type = type
        if lst is not None:
            self._list = lst

    def items(self) -> list[AST | ASTToken]:
        return self._list

    def __getitem__(self, key : int) -> AST | ASTToken:
        return self._list[key]

    def __setitem__(self, key : int, value : AST | ASTToken):
        self._list[key] = value

    def __delitem__(self, key : int):
        self._list.__delitem__[key]

    def __getslice__(self, i : int, j : int) -> list[AST | ASTToken]:
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
            parts = [AST.indent + s for s in parts]
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
                parts = [AST.indent + s for s in str_reps]
                parts_str = "\n".join(parts)
                if parts_str.strip()[0] != "(":
                    parts_str = parts_str.strip()
                    return f"({self.type} {parts_str})"

                return f"({self.type}\n{parts_str})"

    def __iter__(self):
        return self._list.__iter__()


ASTElements = List[Union[AST, ASTToken]]
