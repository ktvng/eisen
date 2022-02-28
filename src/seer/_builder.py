from __future__ import annotations
from distutils.command.build import build
from readline import clear_history
from sys import float_repr_style
from tracemalloc import clear_traces
from alpaca.parser import AbstractBuilder, CommonBuilder, CommonBuilder2
from alpaca.asts import ASTNode, CLRRawList, CLRList, CLRToken
from alpaca.config import Config
from error import Raise


class Builder2(AbstractBuilder):
    build_map = {}

    @classmethod
    def _filter(cls, config : Config, components : CLRRawList) -> CLRRawList:
        return [c for c in components 
            if  (isinstance(c, CLRToken) 
                    and not config.type_hierachy.is_child_type(c.type, "keyword")
                    and not config.type_hierachy.is_child_type(c.type, "symbol")
                    and not config.type_hierachy.is_child_type(c.type, "operator"))
                or isinstance(c, CLRList)]
         
    @AbstractBuilder.build_procedure(build_map, "filter_build")
    def filter_build_(
            config : Config,
            components : CLRRawList, 
            *args) -> CLRRawList:

        newCLRList = CommonBuilder2.build(config, components, *args)[0]
        filtered_children = Builder2._filter(config, newCLRList)

        newCLRList[:] = filtered_children
        return [newCLRList]

    @AbstractBuilder.build_procedure(build_map, "filter_pass")
    def filter_pass(
            config : Config,
            components : CLRRawList,
            *args) -> CLRRawList:

        return Builder2._filter(config, components)
        
    @AbstractBuilder.build_procedure(build_map, "handle_call")
    def filter_pass(
            config : Config,
            components : CLRRawList,
            *args) -> CLRRawList:

        # EXPR . FUNCTION_CALL
        function_call = components[2]
        if not isinstance(function_call, CLRList):
            Raise.error("function call should be CLRList")

        params = function_call[1]
        params[:] = [components[0], *params]

        return function_call

    @AbstractBuilder.build_procedure(build_map, "promote")
    def promote_(
            config : Config,
            components : CLRRawList, 
            type_name : str, 
            *args) -> CLRRawList:

        matches = [x for x in components if x.type[-1] == type_name]
        if len(matches) != 1:
            Raise.code_error("multiple matches during promote_")
        
        captain = matches[0]
        captain[:] = [x for x in components if x != captain]
        return [captain]

    @AbstractBuilder.build_procedure(build_map, "merge")
    def merge_(
            config : Config,
            components : CLRRawList, 
            *args) -> CLRRawList:

        flattened_comps = CommonBuilder2.flatten_components(components)

        if len(flattened_comps) == 2:
            Raise.code_error("unimplemented unary ops")
        elif len(flattened_comps) == 3:
            newCLRList = CLRList(
                flattened_comps[1].value, 
                [flattened_comps[0], flattened_comps[2]], 
                flattened_comps[1].line_number)
            return [newCLRList]
        else:
            Raise.code_error("should not merge with more than 3 nodes")

    @AbstractBuilder.build_procedure(build_map, "handle_op_pref")
    def handle_op_pref(
            config : Config,
            components : CLRRawList,
            *args) -> CLRRawList:

        flattened_comps = CommonBuilder2.flatten_components(components)
        if len(flattened_comps) != 2:
            Raise.error("expected size 2 for handle_op_pref")

        return [CLRList(flattened_comps[0], [flattened_comps[1]]), flattened_comps[0].line_number]


    @classmethod
    def postprocess(cls, node : ASTNode) -> None:
        return
        if node.match_with() == "let" and node.children[0].match_with() == ":":
            # remove the ':' node underneath let
            node.children = node.children[0].children

        for child in node.children:
            cls.postprocess(child) 


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


class Builder(AbstractBuilder):
    build_map = {}

    @AbstractBuilder.build_procedure(build_map, "test")
    def test(components : list[ASTNode], *args):
        print("here")

    @AbstractBuilder.build_procedure(build_map, "filter_build")
    def filter_build_(components : list[ASTNode], *args) -> list[ASTNode]:
        newnode = CommonBuilder.build(components, *args)[0]
        filtered_children = [c for c in newnode.children if
            (c.type != "keyword" and c.type != "symbol")]

        newnode.children = filtered_children
        newnode.children = filtered_children
        return [newnode]

    @AbstractBuilder.build_procedure(build_map, "promote")
    def promote_(components : list[ASTNode], type_name : str, *args) -> list[ASTNode]:
        matches = [x for x in components if x.type == type_name]
        if len(matches) != 1:
            Raise.code_error("multiple matches during promote_")
        
        captain = matches[0]
        captain.children = [x for x in components if x != captain]
        return [captain]

    @AbstractBuilder.build_procedure(build_map, "merge")
    def merge_(components : list[ASTNode], *args) -> list[ASTNode]:
        flattened_comps = CommonBuilder.flatten_components(components)

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
    def postprocess(cls, node : ASTNode) -> None:
        if node.match_with() == "let" and node.children[0].match_with() == ":":
            # remove the ':' node underneath let
            node.children = node.children[0].children

        for child in node.children:
            cls.postprocess(child) 


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