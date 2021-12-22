from error import Raise
from astnode import AstNode
from parser.cyk._cykalgo import CYKAlgo

class AstBuilder():
    def __init__(self, astnodes, dp_table):
        self.astnodes = astnodes
        self.dp_table = dp_table

    def run(self):
        if "START" not in map(lambda x: x.name, self.dp_table[-1][0]):
            Raise.error("input is ungramatical")

        starting_entry = [x for x in self.dp_table[-1][0] if x.name == "START"][0]
        ast_list = self._recursive_descent(starting_entry)
        if len(ast_list) != 1:
            Raise.code_error("ast heads not parsed to single state")
        
        asthead = ast_list[0]
        self._postprocess(asthead)

        return asthead

    @classmethod
    def _postprocess(cls, node : AstNode):
        # return
        if node.op == "let" and node.vals[0].op == ":":
            # remove the ':' node underneath let
            node.vals = node.vals[0].vals
            node.left = node.vals[0]
            node.right = node.vals[1]

        if node.op == ":" or node.op == "let":
            if node.left.op == "var_name_tuple":
                for child in node.left.vals:
                    child.convert_var_to_tag()
            else:
                node.left.convert_var_to_tag()
            node.right.convert_var_to_tag()
            return

        if node.op == "function":
            node.vals[0].convert_var_to_tag()

        for child in node.vals:
            AstBuilder._postprocess(child)

    @classmethod
    def reverse_with_pool(cls, components : list) -> list:
        pass_up_list = []
        for component in components:
            if isinstance(component, list):
                pass_up_list += component
            elif isinstance(component, AstNode):
                pass_up_list.append(component)
            else:
                Raise.code_error("reverse engineering with pooling must be either list or AstNode")

        return pass_up_list

    @classmethod
    def reverse_with_merge(cls, components : list) -> list:
        flattened_comps = []
        for comp in components:
            if isinstance(comp, list):
                flattened_comps += comp
            else:
                flattened_comps.append(comp)

        newnode = AstNode()
        if len(flattened_comps) == 2:
            Raise.code_error("unimplemented unary ops")
        elif len(flattened_comps) == 3:
            newnode.line_number = flattened_comps[1].line_number
            newnode.binary(flattened_comps[1].op, flattened_comps[0], flattened_comps[2])
        else:
            Raise.code_error("should not merge with more than 3 nodes")
        
        return [newnode]

    @classmethod
    def reverse_with_build(cls, build_name : str, components : list):
        newnode = AstNode()
        flattened_components = []
        for comp in components:
            if isinstance(comp, list):
                flattened_components += comp
            else:
                flattened_components.append(comp)

        line_number = 0 if not flattened_components else flattened_components[0].line_number
        newnode.line_number = line_number
        
        return [newnode.plural(build_name, flattened_components)]

    @classmethod
    def reverse_with_pass(cls, components : list) -> list:
        return components

    def _recursive_descent(self, entry : CYKAlgo.DpTableEntry) -> list:
        expressional_keywords = ["this", "return"]
        if entry.is_main_diagonal:
            astnode = self.astnodes[entry.x]
            if astnode.type == "symbol":
                return []
            
            # TODO: why does this work?
            elif astnode.type == "keyword" and astnode.op not in expressional_keywords:
                return []
            else:
                return [astnode]

        left = self._recursive_descent(entry.get_left_child(self.dp_table))
        right = self._recursive_descent(entry.get_right_child(self.dp_table)) 


        flag = "build="
        components = [left, right]
        for reversal_step in entry.rule.reverse_with:
            if isinstance(reversal_step, str):
                Raise.code_error("deprecated codepath")
                if reversal_step == "pass":
                    components = AstBuilder.reverse_with_pool(components)
                elif reversal_step == "merge":
                    components = AstBuilder.reverse_with_merge(components)
                elif reversal_step == "pool":
                    components = AstBuilder.reverse_with_pool(components)
                elif reversal_step[0 : len(flag)] == flag:
                    components = AstBuilder.reverse_with_build(reversal_step[len(flag): ], components)

            else:
                if reversal_step.type == "pass":
                    components = AstBuilder.reverse_with_pool(components)
                elif reversal_step.type == "merge":
                    components = AstBuilder.reverse_with_merge(components)
                elif reversal_step.type == "pool":
                    components = AstBuilder.reverse_with_pool(components)
                elif reversal_step.type == "build":
                    components = AstBuilder.reverse_with_build(reversal_step.value, components)
                else:
                    print("FAILURE")

        return components
