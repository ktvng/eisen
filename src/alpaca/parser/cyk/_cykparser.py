from __future__ import annotations

from alpaca.config import Config
from alpaca.parser._builder import Builder 
from alpaca.asts import AST
from alpaca.parser.cyk._cykalgo import CYKAlgo
from alpaca.parser.cyk._cykalgo2 import CYKAlgo2
from alpaca.parser.cyk._astbuilder import AstBuilder2
from alpaca.grammar import CFGNormalizer
from alpaca.lexer import Token

class CYKParser():
    def __new__(cls, config : Config, tokens : list, builder : Builder) -> AST:
        return CYKParser2(config, tokens, builder)

        normer = CFGNormalizer()
        cfg = normer.run(config.cfg)

        algo = CYKAlgo(cfg)
        algo.parse(tokens)

        # print("====================") 
        # print("PRODUCING RULES:")
        # for entry in algo.dp_table[-1][0]:
        #     print(entry.name)

        return AstBuilder.run(algo.asts, algo.dp_table, builder)

class CYKParser2():
    def __new__(cls, config : Config, tokens : list[Token], builder : Builder) -> AST:
        normer = CFGNormalizer()
        cfg = normer.run(config.cfg)
        algo = CYKAlgo2(cfg)
        algo.parse(tokens)
        astbuilder = AstBuilder2()
        return astbuilder.run(config, algo.tokens, algo.dp_table, builder)