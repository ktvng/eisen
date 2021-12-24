from asts._astnode import ASTNode

class AST():
    def __init__(self, head : ASTNode):
        self.head = head
        
    def __str__(self):
        return self.head.rs_to_string()