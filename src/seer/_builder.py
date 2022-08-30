from __future__ import annotations
from alpaca.parser import CommonBuilder
from alpaca.asts import CLRRawList, CLRList
from alpaca.config import Config
from error import Raise


class Builder(CommonBuilder):
    @CommonBuilder.for_procedure("filter_build")
    def filter_build_(
            fn,
            config : Config,
            components : CLRRawList, 
            *args) -> CLRRawList: 

        newCLRList = Builder.build(fn, config, components, *args)[0]
        filtered_children = Builder._filter(config, newCLRList)

        newCLRList[:] = filtered_children
        return [newCLRList]

    @CommonBuilder.for_procedure("filter_pass")
    def filter_pass(
            fn,
            config : Config,
            components : CLRRawList,
            *args) -> CLRRawList:

        return Builder._filter(config, components)
        
    @CommonBuilder.for_procedure("handle_call")
    def handle_call(
            fn,
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

    @CommonBuilder.for_procedure("promote")
    def promote_(
            fn,
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

    @CommonBuilder.for_procedure("merge")
    def merge_(
            fn,
            config : Config,
            components : CLRRawList, 
            *args) -> CLRRawList:

        flattened_comps = CommonBuilder.flatten_components(components)

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

    @CommonBuilder.for_procedure("handle_op_pref")
    def handle_op_pref(
            fn,
            config : Config,
            components : CLRRawList,
            *args) -> CLRRawList:

        flattened_comps = CommonBuilder.flatten_components(components)
        if len(flattened_comps) != 2:
            Raise.error("expected size 2 for handle_op_pref")

        return [CLRList(flattened_comps[0], [flattened_comps[1]]), flattened_comps[0].line_number]

    # TODO: artifact from builder2
    # @classmethod
    # def postprocess(cls, node : ASTNode) -> None:
    #     return
    #     if node.match_with() == "let" and node.children[0].match_with() == ":":
    #         # remove the ':' node underneath let
    #         node.children = node.children[0].children

    #     for child in node.children:
    #         cls.postprocess(child) 


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
