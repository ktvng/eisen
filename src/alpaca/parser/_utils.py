from alpaca.asts import ASTNode
from alpaca.lexer._token import Token

def tokens_to_astnode(token : Token) -> ASTNode:
    value = token.value if token.rule.value is None else token.rule.value
    match_with = "type" if token.rule.value is None else "value"
    astnode = ASTNode(
        type=token.type, 
        value=value,
        match_with=match_with,
        children=[])

    astnode.line_number = token.line_number

    return astnode