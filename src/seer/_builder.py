from __future__ import annotations
from alpaca.parser import CommonBuilder
from alpaca.clr import CLRRawList, CLRList
from alpaca.config import Config

class SeerBuilder(CommonBuilder):
    @CommonBuilder.for_procedure("filter_build")
    def filter_build_(
            fn,
            config : Config,
            components : CLRRawList, 
            *args) -> CLRRawList: 

        newCLRList = SeerBuilder.build(fn, config, components, *args)[0]
        filtered_children = SeerBuilder._filter(config, newCLRList)

        newCLRList[:] = filtered_children
        return [newCLRList]

    @CommonBuilder.for_procedure("filter_pass")
    def filter_pass(
            fn,
            config : Config,
            components : CLRRawList,
            *args) -> CLRRawList:

        return SeerBuilder._filter(config, components)
        
    @CommonBuilder.for_procedure("handle_call")
    def handle_call(
            fn,
            config : Config,
            components : CLRRawList,
            *args) -> CLRRawList:

        # EXPR . FUNCTION_CALL
        function_call = components[2]
        if not isinstance(function_call, CLRList):
            raise Exception("function call should be CLRList")

        params = function_call[1]
        params[:] = [components[0], *params]

        return function_call

    # instead of having cases of (def ...) that may have a different number of children
    # due to the absence/presence of a (ret ...) child, we homogenize all (def ...) nodes
    # so all with have args, rets, and seq.
    @CommonBuilder.for_procedure("build_def")
    def handle_def(
            fn,
            config : Config,
            components : CLRRawList,
            *args) -> CLRRawList:
        
        newCLRList = SeerBuilder.filter_build_(fn, config, components, "def")[0]
        if len(newCLRList) == 3:
            newCLRList._list.insert(2, CLRList(type="rets", lst=[]))
        return [newCLRList]

    @CommonBuilder.for_procedure("promote")
    def promote_(
            fn,
            config : Config,
            components : CLRRawList, 
            type_name : str, 
            *args) -> CLRRawList:

        matches = [x for x in components if x.type[-1] == type_name]
        if len(matches) != 1:
            raise Exception("multiple matches during promote_")
        
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
            raise Exception("unimplemented unary ops")
        elif len(flattened_comps) == 3:
            newCLRList = CLRList(
                flattened_comps[1].value, 
                [flattened_comps[0], flattened_comps[2]], 
                flattened_comps[1].line_number)
            return [newCLRList]
        else:
            raise Exception("should not merge with more than 3 nodes")

    @CommonBuilder.for_procedure("handle_op_pref")
    def handle_op_pref(
            fn,
            config : Config,
            components : CLRRawList,
            *args) -> CLRRawList:

        flattened_comps = CommonBuilder.flatten_components(components)
        if len(flattened_comps) != 2:
            raise Exception("expected size 2 for handle_op_pref")

        return [CLRList(flattened_comps[0], [flattened_comps[1]]), flattened_comps[0].line_number]

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
