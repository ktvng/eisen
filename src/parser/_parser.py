from grammar import CFGNormalizer
from asts import AST
from parser.cyk import CYKAlgo, AstBuilder
from parser._abstractbuilder import AbstractBuilder
from config import Config

from error import Raise

class Parser():
    @classmethod
    def run(cls, config : Config, tokens : list, builder : AbstractBuilder, algo : str="cyk") -> AST:
        if not tokens:
            return None

        if algo == "cyk":
            return CYKParser.run(config, tokens, builder)
        else:
            Raise.code_error("Error: unknown parser algo")



class CYKParser():
    @classmethod
    def run(cls, config : Config, tokens : list, builder : AbstractBuilder) -> AST:
        normer = CFGNormalizer()
        cfg = normer.run(config.cfg)

        algo = CYKAlgo(cfg)
        algo.parse(tokens)

        # print("====================") 
        # print("PRODUCING RULES:")
        # for entry in algo.dp_table[-1][0]:
        #     print(entry.name)

        ab = AstBuilder(algo.asts, algo.dp_table, builder)
        return ab.run()
