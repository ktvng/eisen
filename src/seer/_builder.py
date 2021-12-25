from __future__ import annotations
from alpaca import parser
from alpaca import asts
from error import Raise

class Builder(parser.AbstractBuilder):
    build_map = {}

    @parser.AbstractBuilder.build_procedure(build_map, "test")
    def test(components : list[asts.ASTNode], *args):
        print("here")

    @parser.AbstractBuilder.build_procedure(build_map, "filter_build")
    def filter_build_(components : list[ASTNode], *args) -> list[ASTNode]:
        newnode = parser.CommonBuilder.build(components, *args)[0]
        filtered_children = [c for c in newnode.children if
            (c.type != "keyword" and c.type != "symbol")]

        newnode.children = filtered_children
        newnode.children = filtered_children
        return [newnode]

    @parser.AbstractBuilder.build_procedure(build_map, "promote")
    def promote_(components : list[ASTNode], type_name : str, *args) -> list[ASTNode]:
        matches = [x for x in components if x.type == type_name]
        if len(matches) != 1:
            Raise.code_error("multiple matches during promote_")
        
        captain = matches[0]
        captain.children = [x for x in components if x != captain]
        return [captain]

    @parser.AbstractBuilder.build_procedure(build_map, "merge")
    def merge_(components : list[ASTNode], *args) -> list[ASTNode]:
        flattened_comps = parser.CommonBuilder.flatten_components(components)

        # TODO: this should be abstracted out. Allow for custom build methods
        if len(flattened_comps) == 2:
            Raise.code_error("unimplemented unary ops")
        elif len(flattened_comps) == 3:
            newnode = asts.ASTNode(
                type=flattened_comps[1].type,
                value=flattened_comps[1].value,
                match_with="value",
                children=[flattened_comps[0], flattened_comps[2]])

            newnode.line_number = flattened_comps[1].line_number
            return [newnode]
        else:
            Raise.code_error("should not merge with more than 3 nodes")
        


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