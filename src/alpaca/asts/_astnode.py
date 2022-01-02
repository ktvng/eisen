
from __future__ import annotations
from error import Raise

class ASTNode():
    def __init__(self, type : str, value : str, match_with : str, children : list[ASTNode]):
        self.type = type
        self.value = value
        self.children = children

        self.compile_data = None
        self.visitor = None
        self.line_number = None
        self._match_with = match_with

    def __str__(self):
        type = "" if self.value == "none" else self.value
        return f"{self.type} {type}"

    def print(self):
        print(self.rs_to_string(), end="")

    def rs_to_string(self, str_rep : str="", indent : int=0, node : ASTNode=None):
        str_rep += indent*"  "
        if node is not None and node == self:
            str_rep += ">"
            
        str_rep += str(self)  + "\n"
        for child in self.children:
            str_rep += child.rs_to_string("", indent+1)

        return str_rep

    def match_with(self):
        if self._match_with == "type":
            return self.type
        elif self._match_with == "value":
            return self.value
        else:
            Raise.code_error(f"unknown match with value {self._match_with}")
