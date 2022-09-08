from __future__ import annotations
from alpaca.config import Config
from alpaca.parser._builder import Builder
from alpaca.clr import AST
from alpaca.lexer import Token

class LR1Parser:
    def __new__(cls, config : Config, tokens : list[Token], builder : Builder) -> AST:
        pass