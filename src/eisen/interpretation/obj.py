from __future__ import annotations
from typing import Any

class Obj:
    def __init__(self, value: Any, name: str = "anon", is_var: bool = False):
        self.value = value
        self.name = name
        self.is_var = is_var

    lambda_map = {
        "+": lambda x, y: x + y,
        "-": lambda x, y: x - y,
        "/": lambda x, y: x // y,
        "*": lambda x, y: x * y,
        "<": lambda x, y: x < y,
        "<=": lambda x, y: x <= y,
        "==": lambda x, y: x == y,
        "!=": lambda x, y: x != y,
        ">": lambda x, y: x > y,
        ">=": lambda x, y: x >= y,
        "or": lambda x, y: x or y,
        "and": lambda x, y: x and y,
    }
    @classmethod
    def apply_binary_operation(cls, op: str, obj1: Obj, obj2: Obj):
        if op in Obj.lambda_map:
            return Obj(Obj.lambda_map[op](obj1.value, obj2.value))
        else:
            raise Exception(f"unhandled binary operation {op}")

    def __str__(self) -> str:
        return str(self.value)

    def get_debug_str(self) -> str:
        return f"{self.name}:{self.value}"

    def get(self, key: str):
        if not isinstance(self.value, dict):
            raise Exception(f"Interpreter object must be a dict (for struct), but got {type(self.value)}")
        found = self.value.get(key, None)
        if found is None:
            new_obj = Obj(None)
            self.value[key] = new_obj
            found = new_obj
        return found
