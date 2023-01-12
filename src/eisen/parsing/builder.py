from __future__ import annotations
from alpaca.parser import CommonBuilder
from alpaca.clr import CLRRawList, CLRList
from alpaca.config import Config

class EisenBuilder(CommonBuilder):
    # instead of having cases of (def ...) that may have a different number of children
    # due to the absence/presence of a (ret ...) child, we homogenize all (def ...) nodes
    # so all with have args, rets, and seq.
    @CommonBuilder.for_procedure("build_def")
    def handle_def(
            fn,
            config : Config,
            components : CLRRawList,
            *args) -> CLRRawList:

        newCLRList = EisenBuilder.filter_build_(fn, config, components, "def")[0]
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

    @CommonBuilder.for_procedure("handle_op_pref")
    def handle_op_pref(
            fn,
            config : Config,
            components : CLRRawList,
            *args) -> CLRRawList:

        flattened_comps = CommonBuilder.flatten_components(components)
        if len(flattened_comps) != 2:
            raise Exception("expected size 2 for handle_op_pref")

        return [CLRList(
            type=flattened_comps[0].type,
            lst=[flattened_comps[1]],
            line_number=flattened_comps[0].line_number)]
