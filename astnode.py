
from __future__ import annotations
from error import Raise

class AstNode():
    def __init__(self):
        self.type = "none"
        self.compile_data = None
        self.vals = []
        self.line_number = None

    def _common_init(self, type : str, op : str, vals : list, match_with : str) -> None:
        self.type = type
        self.op = op
        self.vals = vals
        self.match_with = match_with

    def binary(self, op : str, left : AstNode, right : AstNode):
        self._common_init("binary", op, [left, right], op)
        
        self.left = left
        self.right = right

        return self

    def unary(self, op : str, val : AstNode):
        self._common_init("unary", op, [val], op)

        self.val = val
        return self

    def leaf(self, val : str):
        self._common_init("leaf", "var", [], "var")
        self.leaf_val = val

        return self

    def literal(self, op : str, val : str):
        self._common_init("literal", op, [], match_with="literal")
        self.literal_val = val

        return self

    def plural(self, op : str, vals : list):
        self._common_init("plural", op, vals, op)

        return self

    def keyword(self, val : str):
        self._common_init("keyword", val, [], val)

        return self

    def operator(self, val : str, match_with : str):
        self._common_init("operator", val, [], match_with)

        return self

    def symbol(self, val : str):
        self._common_init("symbol", "", [], val)

        return self

    def convert_var_to_tag(self):
        if self.type == "leaf" and self.op == "var":
            self.op = "tag"

    def print(self, indent=0):
        print(self.rs_to_string(), end="")
        
    def rs_to_string(self, str_rep : str="", indent : int=0, node : AstNode=None):
        str_rep += indent*" "
        if node is not None and node == self:
            str_rep += ">"
            
        if self.type == "unary":
            str_rep += str(self.op)
            self.val.rs_to_string(str_rep, indent+1)
        elif self.type == "binary":
            str_rep += str(self.op) + "\n"
            str_rep += self.left.rs_to_string("", indent+1)
            str_rep += self.right.rs_to_string("", indent+1)
        elif self.type == "plural":
            str_rep += str(self.op) + "\n"
            for node in self.vals:
                str_rep += node.rs_to_string("", indent+1)
        elif self.type == "leaf":
            str_rep += f"{self.op} {self.leaf_val}\n"
        elif self.type == "keyword" or self.type == "operator":
            str_rep += str(self.op) + "\n"
        elif self.type == "literal":
            str_rep += f"{self.op} {self.literal_val}\n"
        else:
            Raise.code_error(f"unimplemented astnode type: ({self.type})")
        
        return str_rep
