from __future__ import annotations

from alpaca.config import Config
from alpaca.parser._builder import Builder
from alpaca.clr._clr import AST
from alpaca.parser.cyk._cykalgo import CYKAlgo
from alpaca.parser.cyk._astbuilder import AstBuilder
from alpaca.grammar import CFGNormalizer
from alpaca.lexer import Token

class CYKParser():
    def __new__(cls, config : Config, tokens : list[Token], builder : Builder) -> AST:
        normer = CFGNormalizer()
        cfg = normer.run(config.cfg)
        algo = CYKAlgo(cfg)
        algo.parse(tokens)
        astbuilder = AstBuilder()
        return astbuilder.run(config, algo.tokens, algo.dp_table, builder)
