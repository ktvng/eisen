
from __future__ import annotations
from error import Raise

class AstNode():
    def __init__(self):
        self.type = "none"
        self.compile_data = None
        self.vals = []

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

    def rsprint(self, indent=0):
        print(indent*" ", end="")
        if self.type == "unary":
            print(self.op, end="")
            self.val.rsprint(indent+1)
        elif self.type == "binary":
            print(self.op)
            self.left.rsprint(indent+1)
            self.right.rsprint(indent+1)
        elif self.type == "plural":
            print(self.op)
            for node in self.vals:
                node.rsprint(indent+1)
        elif self.type == "leaf":
            print(self.op, self.leaf_val)
        elif self.type == "keyword" or self.type == "operator":
            print(self.op)
        elif self.type == "literal":
            print(self.op, self.literal_val)
        else:
            Raise.code_error("unimplemented astnode type")
        


