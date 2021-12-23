from ast._astnode import AstNode

class AST():
    def __init__(self, head : AstNode):
        self.head = head
        
    def __str__(self):
        return self.head.rs_to_string()