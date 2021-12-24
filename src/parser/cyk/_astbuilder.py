from error import Raise
from asts import AST, ASTNode
from parser.cyk._cykalgo import CYKAlgo

class AstBuilder():
    def __init__(self, astnodes, dp_table):
        self.astnodes = astnodes
        self.dp_table = dp_table

    def run(self) -> AST:
        if "START" not in map(lambda x: x.name, self.dp_table[-1][0]):
            Raise.error("input is ungramatical")

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
        if node.op == "let" and node.vals[0].op == ":":
            # remove the ':' node underneath let
            node.vals = node.vals[0].vals

        for child in node.vals:
            AstBuilder._postprocess(child)

    @classmethod
    def reverse_with_pool(cls, components : list) -> list:
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
    def reverse_with_convert(cls, name : str, components : list) -> list:
        if len(components) != 1:
            Raise.code_error("expects size of 1")

        components[0].type = name
        components[0].op = name        
        return components


    @classmethod
    def reverse_with_merge(cls, components : list) -> list:
        flattened_comps = []
        for comp in components:
            if isinstance(comp, list):
                flattened_comps += comp
            else:
                flattened_comps.append(comp)

        # TODO: this should be abstracted out. Allow for custom build methods
        if len(flattened_comps) == 2:
            Raise.code_error("unimplemented unary ops")
        elif len(flattened_comps) == 3:
            newnode = ASTNode(
                type=flattened_comps[1].type,
                value=flattened_comps[1].op,
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
    @classmethod
    def reverse_with_build(cls, build_name : str, components : list):
        flattened_components = []
        for comp in components:
            if isinstance(comp, list):
                flattened_components += comp
            else:
                flattened_components.append(comp)

        newnode = ASTNode(
            type=build_name,
            value="none",
            match_with="type",
            children=flattened_components)

        line_number = 0 if not flattened_components else flattened_components[0].line_number
        newnode.line_number = line_number

        return [newnode]

    @classmethod
    def reverse_with_pass(cls, components : list) -> list:
        return components

    def _recursive_descent(self, entry : CYKAlgo.DpTableEntry) -> list:
        expressional_keywords = ["this", "return", "RETURN"]
        if entry.is_main_diagonal:
            astnode = self.astnodes[entry.x]
            if astnode.type == "symbol":
                return []
            
            # TODO: why does this work?
            # answer: probably because we need return to be an operator
            elif astnode.type == "keyword" and astnode.op not in expressional_keywords:
                return []
            else:
                components = [astnode]
        
        else:
            left = self._recursive_descent(entry.get_left_child(self.dp_table))
            right = self._recursive_descent(entry.get_right_child(self.dp_table)) 

            components = [left, right]

        for reversal_step in entry.rule.reverse_with:
            print(entry.rule)
            if isinstance(reversal_step, str):
                Raise.code_error("deprecated codepath")

            else:
                if reversal_step.type == "pass":
                    components = AstBuilder.reverse_with_pool(components)
                elif reversal_step.type == "merge":
                    components = AstBuilder.reverse_with_merge(components)
                elif reversal_step.type == "pool":
                    components = AstBuilder.reverse_with_pool(components)
                elif reversal_step.type == "build":
                    components = AstBuilder.reverse_with_build(reversal_step.value, components)
                elif reversal_step.type == "convert":
                    components = AstBuilder.reverse_with_convert(reversal_step.value, components)
                else:
                    print("FAILURE")

        return components
