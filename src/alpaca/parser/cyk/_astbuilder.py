from __future__ import annotations
from re import A

from error import Raise
from alpaca.asts import AST, ASTNode, CLRList, CLRToken, CLRRawList
from alpaca.parser.cyk._cykalgo import CYKAlgo
from alpaca.parser.cyk._cykalgo2 import CYKAlgo2, DpTable, DpTableEntry
from alpaca.parser._abstractbuilder import AbstractBuilder
from alpaca.parser._commonbuilder import CommonBuilder
from alpaca.parser._commonbuilder2 import CommonBuilder2
from alpaca.config import Config

class AstBuilder():
    @classmethod
    def run(cls, nodes : list[ASTNode], dp_table, builder : AbstractBuilder) -> AST:
        cls.nodes = nodes
        cls.dp_table = dp_table
        cls.builder = builder

        common_build_map = CommonBuilder.build_map
        builder_build_map = {} if builder is None else builder.build_map
        cls.build_map = { **common_build_map, **builder_build_map }

        if "START" not in map(lambda x: x.name, cls.dp_table[-1][0]):
            Raise.error("input is ungrammatical")

        starting_entry = [x for x in cls.dp_table[-1][0] if x.name == "START"][0]
        ast_list = cls._recursive_descent(starting_entry)
        if len(ast_list) != 1:
            Raise.code_error("ast heads not parsed to single state")
        
        asthead = ast_list[0]
        if builder is not None:
            cls.builder.postprocess(asthead)

        return AST(asthead)

    @classmethod
    def _recursive_descent(cls, entry : CYKAlgo.DpTableEntry) -> list:
        if entry.is_main_diagonal:
            astnode = cls.nodes[entry.x]
            components = [astnode]
        else:
            left = cls._recursive_descent(entry.get_left_child(cls.dp_table))
            right = cls._recursive_descent(entry.get_right_child(cls.dp_table)) 
            components = [left, right]

        for reversal_step in entry.rule.actions:
            build_procedure = cls.build_map.get(reversal_step.type, None)
            if build_procedure is None:
                Raise.code_error(f"build procedure {reversal_step.type} not found by ast_builder")

            components = build_procedure(components, reversal_step.value)

        return components

class AstBuilder2:
    def _contruct_build_map(self, builder : AbstractBuilder):
        common_build_map = CommonBuilder2.build_map
        builder_build_map = {} if builder is None else builder.build_map
        self.build_map = { **common_build_map, **builder_build_map }

    def run(self, config : Config, nodes : list[CLRToken], dp_table : DpTable, builder : AbstractBuilder) -> CLRList:
        self.config = config
        self.nodes = nodes
        self.dp_table = dp_table
        self._contruct_build_map(builder)

        if "START" not in map(lambda x: x.name, dp_table[-1][0]):
            Raise.error("'START' not found at top level: input is ungrammatical")

        starting_entry = [x for x in dp_table[-1][0] if x.name == "START"][0]
        clrList = self._recursive_descent(starting_entry)
        if len(clrList) != 1:
            Raise.code_error("ast heads not parsed to single state")
        
        head = clrList[0]
        # if builder is not None:
        #     self.builder.postprocess(head)

        return head

    def _recursive_descent(self, entry : DpTableEntry) -> CLRRawList:

        if entry.is_main_diagonal:
            components = [self.nodes[entry.x]]
        else:
            left = self._recursive_descent(
                entry.get_left_child(self.dp_table))

            right = self._recursive_descent(
                entry.get_right_child(self.dp_table))

            components = [left, right]

        for reversal_step in entry.rule.actions:
            build_procedure = self.build_map.get(reversal_step.type, None)
            if build_procedure is None:
                Raise.code_error(f"build procedure {reversal_step.type} not found by ast_builder")

            components = build_procedure(self.config, components, reversal_step.value)

        return components 