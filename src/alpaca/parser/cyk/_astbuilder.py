from __future__ import annotations

from alpaca.asts import CLRList, CLRToken, CLRRawList
from alpaca.parser.cyk._cykalgo import DpTable, DpTableEntry
from alpaca.parser._builder import Builder
from alpaca.config import Config

class AstBuilder:
    def run(self, config : Config, nodes : list[CLRToken], dp_table : DpTable, builder : Builder) -> CLRList:
        self.config = config
        self.nodes = nodes
        self.dp_table = dp_table
        self.builder = builder

        if "START" not in map(lambda x: x.name, dp_table[-1][0]):
            raise Exception("'START' not found at top level: input is ungrammatical")

        starting_entry = [x for x in dp_table[-1][0] if x.name == "START"][0]
        clrList = self._recursive_descent(starting_entry)
        if len(clrList) != 1:
            raise Exception("ast heads not parsed to single state")
        
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
            components = self.builder.apply(reversal_step.type, self.config, components, reversal_step.value)

        return components 