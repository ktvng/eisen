from __future__ import annotations
from alpaca.parser import CommonBuilder
from alpaca.clr import ASTElements, AST
from alpaca.config import Config

class EisenBuilder(CommonBuilder):
    # instead of having cases of (def ...) that may have a different number of children
    # due to the absence/presence of a (ret ...) child, we homogenize all (def ...) nodes
    # so all with have args, rets, and seq.
    @CommonBuilder.for_procedure("build_def")
    def handle_def(
            fn,
            config : Config,
            components : ASTElements,
            *args) -> ASTElements:

        newCLRList = EisenBuilder.filter_build_(fn, config, components, "def")[0]
        if len(newCLRList) == 3:
            newCLRList._list.insert(2, AST(type="rets", lst=[]))
        return [newCLRList]

    @CommonBuilder.for_procedure("handle_op_pref")
    def handle_op_pref(
            fn,
            config : Config,
            components : ASTElements,
            *args) -> ASTElements:

        flattened_comps = CommonBuilder.flatten_components(components)
        if len(flattened_comps) != 2:
            raise Exception("expected size 2 for handle_op_pref")

        return [AST(
            type=flattened_comps[0].type,
            lst=[flattened_comps[1]],
            line_number=flattened_comps[0].line_number)]

    @CommonBuilder.for_procedure("convert_decl")
    def convert_decl_(
            fn,
            config: Config,
            components: ASTElements,
            name: str,
            *args) -> ASTElements:
        """this converts (let (: A B)) into (let A B) to remove
        the extraneous (: ...) """

        typing_component = components[-1]
        typing_component.type = name
        return [typing_component]

    # TODO: restored, but this is a hack and should be removed
    @CommonBuilder.for_procedure("strip_annotation")
    def strip_annotation(
            fn,
            config: Config,
            components: ASTElements,
            name: str,
            *args) -> ASTElements:

        typing_component = components[-1]
        return [typing_component]
