from alpaca.config import Config
from alpaca.parser._abstractbuilder import AbstractBuilder
from alpaca.asts import AST
from alpaca.parser.cyk._cykalgo import CYKAlgo
from alpaca.parser.cyk._astbuilder import AstBuilder
from alpaca.grammar import CFGNormalizer

class CYKParser():
    def __new__(cls, config : Config, tokens : list, builder : AbstractBuilder) -> AST:
        normer = CFGNormalizer()
        cfg = normer.run(config.cfg)

        algo = CYKAlgo(cfg)
        algo.parse(tokens)

        # print("====================") 
        # print("PRODUCING RULES:")
        # for entry in algo.dp_table[-1][0]:
        #     print(entry.name)

        return AstBuilder.run(algo.asts, algo.dp_table, builder)
