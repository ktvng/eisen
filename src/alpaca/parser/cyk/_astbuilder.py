from __future__ import annotations

from error import Raise
from alpaca.asts import AST, ASTNode
from alpaca.parser.cyk._cykalgo import CYKAlgo
from alpaca.parser._abstractbuilder import AbstractBuilder
from alpaca.parser._commonbuilder import CommonBuilder

class AstBuilder():
    def __init__(self, nodes : list[ASTNode], dp_table, builder : AbstractBuilder):
        self.nodes = nodes
        self.dp_table = dp_table
        self.builder = builder

        common_build_map = CommonBuilder.build_map
        builder_build_map = {} if builder is None else builder.build_map
        self.build_map = { **common_build_map, **builder_build_map }

    def run(self) -> AST:
        if "START" not in map(lambda x: x.name, self.dp_table[-1][0]):
            Raise.error("input is ungrammatical")

        starting_entry = [x for x in self.dp_table[-1][0] if x.name == "START"][0]
        ast_list = self._recursive_descent(starting_entry)
        if len(ast_list) != 1:
            Raise.code_error("ast heads not parsed to single state")
        
        asthead = ast_list[0]
        self.builder.postprocess(asthead)

        return AST(asthead)


    def _recursive_descent(self, entry : CYKAlgo.DpTableEntry) -> list:
        if entry.is_main_diagonal:
            astnode = self.nodes[entry.x]
            components = [astnode]
        else:
            left = self._recursive_descent(entry.get_left_child(self.dp_table))
            right = self._recursive_descent(entry.get_right_child(self.dp_table)) 
            components = [left, right]

        for reversal_step in entry.rule.actions:
            build_procedure = self.build_map.get(reversal_step.type, None)
            if build_procedure is None:
                Raise.code_error(f"build procedure {reversal_step.type} not found by ast_builder")

            components = build_procedure(components, reversal_step.value)

        return components
