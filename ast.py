
from __future__ import annotations
from error import Raise

class AstNode():
    def __init__(self):
        self.type = "none"

    def binary(self, op : str, left : AstNode, right : AstNode):
        self.type = "binary"
        self.op = op
        self.left = left
        self.right = right
        self.match_with = op
        return self

    def unary(self, op : str, val : AstNode):
        self.type = "unary"
        self.op = op
        self.val = val
        self.match_with = op
        return self

    def leaf(self, val : str):
        self.type = "leaf"
        self.match_with = "var"
        self.val = val
        return self

    def plural(self, op : str, vals : list):
        self.type = "plural"
        self.op = op
        self.match_with = op
        self.vals = vals
        return self

    def keyword(self, val : str):
        self.type = "keyword"
        self.val = val
        self.match_with = val
        return self

    def operator(self, val : str, match_with : str):
        self.type = "operator"
        self.val = val
        self.match_with = match_with
        return self

    def symbol(self, val : str):
        self.type = "symbol"
        self.match_with = val
        return self

    def connector(self, name : str, left : AstNode, right : AstNode):
        self.type = "connector"
        self.name = name
        self.match_with = name
        self.vals = []
        
        if left.type == "connector":
            self.vals += left.vals
        else:
            self.vals.append(left)
        
        if right.type == "connector":
            self.vals += right.vals
        else:
            self.vals.append(right)

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
        elif self.type == "leaf" or self.type == "keyword" or self.type == "operator":
            print(self.val)
        else:
            Raise.code_error("unimplemented astnode type")
        


