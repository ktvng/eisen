from __future__ import annotations
from alpaca.config import Config
from alpaca.parser._abstractbuilder import AbstractBuilder
from alpaca.asts import AST
from alpaca.lexer import Token

class LR1Parser:
    def __new__(cls, config : Config, tokens : list[Token], builder : AbstractBuilder) -> AST:
        pass