from __future__ import annotations

from error import Raise
from asts import AST, ASTNode
from parser.cyk._cykalgo import CYKAlgo

class AstBuilder():
    def __init__(self, nodes : list[ASTNode], dp_table):
        self.nodes = nodes
        self.dp_table = dp_table
        self.build_map = self._get_standard_build_map()

    def run(self) -> AST:
        if "START" not in map(lambda x: x.name, self.dp_table[-1][0]):
            Raise.error("input is ungrammatical")

        starting_entry = [x for x in self.dp_table[-1][0] if x.name == "START"][0]
        ast_list = self._recursive_descent(starting_entry)
        if len(ast_list) != 1:
            Raise.code_error("ast heads not parsed to single state")
        
        asthead = ast_list[0]
        self._postprocess(asthead)

        return AST(asthead)

    # TODO: this should be abstracted out to some seer callback
    @classmethod
    def _postprocess(cls, node : ASTNode):
        # return
        if node.match_with() == "let" and node.children[0].match_with() == ":":
            # remove the ':' node underneath let
            node.children = node.children[0].children

        for child in node.children:
            AstBuilder._postprocess(child)

    @classmethod
    def pool_(cls, components : list[ASTNode], *args) -> list[ASTNode]:
        pass_up_list = []
        for component in components:
            if isinstance(component, list):
                pass_up_list += component
            elif isinstance(component, ASTNode):
                pass_up_list.append(component)
            else:
                Raise.code_error("reverse engineering with pooling must be either list or ASTNode")

        return pass_up_list

    @classmethod
    def convert_(cls, components : list[ASTNode], name : str, *args) -> list[ASTNode]:
        if len(components) != 1:
            Raise.code_error("expects size of 1")

        components[0].type = name
        return components

    @classmethod
    def promote_(cls, components : list[ASTNode], type_name : str, *args) -> list[ASTNode]:
        matches = [x for x in components if x.type == type_name]
        if len(matches) != 1:
            Raise.code_error("multiple matches during promote_")
        
        captain = matches[0]
        captain.children = [x for x in components if x != captain]
        return [captain]

    @classmethod
    def merge_(cls, components : list[ASTNode], *args) -> list[ASTNode]:
        flattened_comps = cls._flatten_components(components)

        # TODO: this should be abstracted out. Allow for custom build methods
        if len(flattened_comps) == 2:
            Raise.code_error("unimplemented unary ops")
        elif len(flattened_comps) == 3:
            newnode = ASTNode(
                type=flattened_comps[1].type,
                value=flattened_comps[1].value,
                match_with="value",
                children=[flattened_comps[0], flattened_comps[2]])

            newnode.line_number = flattened_comps[1].line_number
            return [newnode]
        else:
            Raise.code_error("should not merge with more than 3 nodes")
        
    @classmethod
    def _flatten_components(cls, components : list[ASTNode | list[ASTNode]]) -> list[ASTNode]:
        flattened_components = []
        for comp in components:
            if isinstance(comp, list):
                flattened_components += comp
            else:
                flattened_components.append(comp)

        return flattened_components

    @classmethod
    def _build_internal(cls, 
            components : list[ASTNode], 
            build_name : str, 
            *args) -> ASTNode:

        flattened_components = cls._flatten_components(components)
        if not flattened_components:
            Raise.code_error("flattened_components must not be empty")

        newnode = ASTNode(
            type=build_name,
            value="none",
            match_with="type",
            children=flattened_components)

        newnode.line_number = flattened_components[0].line_number
        return newnode

    # TODO:
    # merge to be replaced with consume
    #
    # @action consume B
    # X -> A B C
    # build would have (1) fix build to do this, takes no arguments
    #            X 
    #         /  |  \
    #        A   B   C
    # 
    # but consume would have
    #            B
    #           / \
    #          A   C
    #
    # and
    # @action consume C
    # X -> A B C
    # yields
    #            C
    #           / \
    #          A   B
    #
    #
    @classmethod
    def build_(cls, components : list[ASTNode], build_name : str, *args) -> list[ASTNode]:
        return [cls._build_internal(components, build_name, *args)]

    @classmethod
    def filter_build_(cls, 
            components : list[ASTNode], 
            build_name : str, 
            *args) -> list[ASTNode]:

        newnode = cls._build_internal(components, build_name, *args)
        filtered_children = [c for c in newnode.children if
            (c.type != "keyword" and c.type != "symbol")]

        newnode.children = filtered_children
        newnode.children = filtered_children
        return [newnode]

    @classmethod
    def pass_(cls, components : list[ASTNode], *args) -> list[ASTNode]:
        return components

    @classmethod
    def _get_standard_build_map(cls):
        build_map = {
            "pass": cls.pass_,
            "build": cls.build_,
            "merge": cls.merge_,
            "convert": cls.convert_,
            "pool": cls.pool_,
            "promote": cls.promote_,
            "filter_build": cls.filter_build_
        }

        return build_map

    def _recursive_descent(self, entry : CYKAlgo.DpTableEntry) -> list:
        if entry.is_main_diagonal:
            astnode = self.nodes[entry.x]
            components = [astnode]
        else:
            left = self._recursive_descent(entry.get_left_child(self.dp_table))
            right = self._recursive_descent(entry.get_right_child(self.dp_table)) 
            components = [left, right]

        for reversal_step in entry.rule.reverse_with:
            build_procedure = self.build_map.get(reversal_step.type, None)
            if build_procedure is None:
                Raise.code_error(f"build procedure {reversal_step.type} not found by ast_builder")

            components = build_procedure(components, reversal_step.value)

        return components
