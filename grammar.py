import ast
from error import Raise
from ast import AstNode
import itertools

def is_op(txt : str) -> bool:
    return txt[0 : 3] == "op_"

OpCodes = {
    "=": "op_assign",
    ":=": "op_assign",
    "<-": "op_assign",
    "+=": "op_assign",
    "-=": "op_assign",
    "*=": "op_assign",
    "/=": "op_assign",
    "?": "op_unary_post",
    "==": "op_bin",
    "!=": "op_bin",
    "->": "->",
    ":": ":",
    "+": "op_bin",
    "-": "op_bin",
    "/": "op_bin",
    "*": "op_bin",
    "&": "&",
    "&&": "op_bin",
    "||": "op_bin",
    "!": "op_unary_pref",
    "%": "op_bin",
    "++": "op_unary_post",
    "--": "op_unary_post", 
    "<<": "op_bin",
    ">>": "op_bin",
    "|": "op_bin",
    "<": "op_bin",
    ">": "op_bin",
    "<=": "op_bin",
    ">=": "op_bin",
    ".": "op_bin",
    ",": ",",
    "//": "none",
    "::": "op_bin",
    "{": "{", 
    "}": "}", 
    "(": "(", 
    ")": ")", 
    "[": "[", 
    "]": "]", 
}

class GrammarRule():
    guid = 0
    def __init__(self, parent : str, pattern_str : str, reverse_with):
        self.guid = GrammarRule.guid
        self.parent = parent.strip()
        self.pattern_str = pattern_str
        self.pattern = [s.strip() for s in pattern_str.split(' ') if s != ""]
        if isinstance(reverse_with, str):
            self.reverse_with = [reverse_with]
        elif isinstance(reverse_with, list):
            self.reverse_with = reverse_with

        self.build_guids = []

        GrammarRule.guid += 1

    @classmethod
    def is_production_rule(cls, token : str):
        return token.isupper() and all(map(lambda x : x.isalnum() or x == '_', token))

    def __str__(self):
        return self.parent + " -> " + self.pattern_str

class CFG():
    def __init__(self, rules : list):
        self.rules = rules
        self.start = "START"

    def set_start(self, start : str):
        self.start = start

class Grammar():
    expressional_keywords = [
        "this",
        "return",
    ]

    grammar_implementation = None

    @classmethod
    def load(cls):
        parser = GrammarParser()
        cls.grammar_implementation = parser.load()
        return cls

    @classmethod 
    def tokens_to_ast_queue(cls, tokens : list) -> list:
        ast_queue = []
        for tok in tokens:
            astnode = AstNode()
            astnode.line_number = tok.line_number
            if tok.type == "var":
                ast_queue.append(astnode.leaf(tok.value))
            elif tok.type == "operator":
                ast_queue.append(astnode.operator(tok.value, match_with=OpCodes[tok.value]))
            elif tok.type == "symbol":
                ast_queue.append(astnode.symbol(tok.value))
            elif tok.type == "keyword":
                ast_queue.append(astnode.keyword(tok.value))
            elif tok.type == "string":
                ast_queue.append(astnode.literal("string", tok.value))
            elif tok.type == "int":
                ast_queue.append(astnode.literal("int", tok.value))
            elif tok.type == "bool":
                ast_queue.append(astnode.literal("bool", tok.value))
            else:
                Raise.code_error("unimplemented token type")

        return ast_queue
class GrammarParser():
    grammar_file = "grammar.txt"
    flag = "@action "

    @classmethod
    def _loadRule(cls, line : str, reverse_with : str) -> GrammarRule:
        parts = line.split('->', 1)
        if len(parts) != 2:
            Raise.error("invalid grammar line; must contain symbol ->")
        
        pattern, pattern_str = parts

        return GrammarRule(pattern, pattern_str, reverse_with)

    @classmethod
    def _defines_reverse_method_decl(cls, line : str) -> bool:
        return cls.flag == line[0 : len(cls.flag)]

    @classmethod
    def _get_reverse_method(cls, line : str) -> str:
        return line[len(cls.flag) : ]

    @classmethod
    def load(cls) -> CFG:
        cached_reverse_with_method = "pass"
        raw_rules = []
        with open(cls.grammar_file, 'r') as f:
            raw_rules = [l.strip() for l in f.readlines() if l.strip() != ""]
            raw_rules = [l for l in raw_rules if l[0] != "#"]

        rules = []
        for line in raw_rules:
            if cls._defines_reverse_method_decl(line):
                cached_reverse_with_method = cls._get_reverse_method(line)
                continue

            rules.append(cls._loadRule(line, cached_reverse_with_method))

        return CFG(rules)

class CYKAlgo():
    def __init__(self, cfg : CFG):
        for rule in cfg.rules:
            if not CFGNormalizer.is_cnf_rule(rule):
                Raise.error("grammar is not normalized")

        self.cfg = cfg

    class DpTableEntry():
        def __init__(self, rule : GrammarRule, x, y, diagonal_number, delta=None, lname=None, rname=None):
            self.rule = rule
            self.name = rule.parent
            self.x = x
            self.y = y
            self.diagonal_number = diagonal_number

            if(delta is None):
                self.is_main_diagonal = True
                return

            self.is_main_diagonal = False 
            self.delta = delta
            self.lname = lname
            self.rname = rname

        def get_left_child(self, dp_table):
            lcx, lcy = CYKAlgo.get_left_child(self.x, self.y, self.diagonal_number, self.delta)
            table_entries = dp_table[lcx][lcy]
            matching_entries = [e for e in table_entries if e.name == self.lname]

            if len(matching_entries) == 0:
                Raise.code_error("reached point in grammatical tree with no children")

            if len(matching_entries) > 1:
                Raise.notice("non-uniqueness, multiple possible production pathways")

            return matching_entries[0]

        def get_right_child(self, dp_table):
            rcx, rcy = CYKAlgo.get_right_child(self.x, self.y, self.diagonal_number, self.delta)
            table_entries = dp_table[rcx][rcy]
            matching_entries = [e for e in table_entries if e.name == self.rname]

            if len(matching_entries) == 0:
                Raise.code_error("reached point in grammatical tree with no children")

            if len(matching_entries) > 1:
                Raise.notice("non-uniqueness, multiple possible production pathways")

            return matching_entries[0]

    def parse(self, tokens : list):
        self.n = len(tokens)
        self.asts = Grammar.tokens_to_ast_queue(tokens)
        self.dp_table = [[[] for y in range(self.n)] for x in range(self.n) ] 
        self._do_parse()

        return self.dp_table

    def _do_parse(self):
        self._fill_first_diagonal()

        for i in range(1, self.n):
            self._fill_diagonal(i)

    def _get_diagonal(self, starting_x : int) -> list:
        x , y = starting_x, 0
        diagonal_points = []
        while x < self.n:
            diagonal_points.append((x, y))
            x += 1
            y += 1
        
        return diagonal_points

    def _get_producing_rules_for_token(self, match_with : str):
        return [rule for rule in self.cfg.rules
            if len(rule.pattern) == 1 and rule.pattern[0] == match_with]

    def _get_producing_rules(self, lname : str, rname : str):
        return [rule for rule in self.cfg.rules
            if len(rule.pattern) == 2 
                and rule.pattern[0] == lname 
                and rule.pattern[1] == rname]

    def _fill_first_diagonal(self):
        diagonal_points = self._get_diagonal(0)
        for point in diagonal_points:
            # x == y for diagonal(0)
            x, y = point

            astnode = self.asts[x]
            producing_rules = self._get_producing_rules_for_token(astnode.match_with)
            entries = [CYKAlgo.DpTableEntry(rule, x, y, 0,) for rule in producing_rules]
            self.dp_table[x][y] = entries

    #
    #       0   1   2   3   4   ... 
    #   0   .
    #   1       A   B   C   x
    #   2           .       A'
    #   3               .   B'
    #   4                   C'
    #   .
    #   .
    #   . 
    #   
    #   A(1,1) produces [1:1]
    #   B(2,1) produces [1:2]

    #   Therefore x at (4,1) must produce [1:4] and therefore B must be matched with 
    #   B'(4,3) which produces [3:4] as [1:2] + [3:4] = [1:4]
    #  
    def _fill_diagonal(self, diagonal_number : int):
        diagonal_points = self._get_diagonal(diagonal_number)
        for point in diagonal_points:
            x, y = point
            for delta in range(diagonal_number):
                left_child_x, left_child_y = CYKAlgo.get_left_child(x, y ,diagonal_number, delta)
                lrule_names = list(map(lambda x: x.name, self.dp_table[left_child_x][left_child_y]))

                right_child_x, right_child_y = CYKAlgo.get_right_child(x, y, diagonal_number, delta)
                rrule_names = list(map(lambda x: x.name, self.dp_table[right_child_x][right_child_y]))

                rule_pairs = itertools.product(lrule_names, rrule_names)
                for rule_pair in rule_pairs:
                    lname, rname = rule_pair
                    producing_rules = self._get_producing_rules(lname, rname)
                    entries = [CYKAlgo.DpTableEntry(rule, x, y, diagonal_number, delta, lname, rname) for rule in producing_rules]
                    self.dp_table[x][y] += entries

    @classmethod
    def get_left_child(cls, x, y, diagonal_number, delta):
        return x-diagonal_number+delta, y

    @classmethod
    def get_right_child(cls, x, y, diagnonal_number, delta):
        return x, y + 1 + delta

    @classmethod
    def is_main_diagonal(cls, x, y):
        return x == y

class CFGNormalizer():
    def __init__(self):
        # maps from literals : str to rules : GrammarRule
        self.literal_tokens = {}
        self.n_literal_tokens = 0
        self.n_connector_rules = 0

        # maps from ruleA:ruleB 
        self.connectors = {} 
        self.rules = []

        self.starting_rule_name = "START"

    def run(self, cfg : CFG):
        self.original_cfg = cfg
        for rule in cfg.rules:
            self._expand_rule(rule)

        new_cfg = CFG(self.rules)
        new_cfg.set_start(self.starting_rule_name)

        return new_cfg

    @classmethod 
    def is_connector(cls, name : str) -> bool:
        return "_CONNECTOR" in name and name[-1] == "_"


    @classmethod
    def is_cnf_rule(cls, rule : GrammarRule):
        if len(rule.pattern) == 2:
            return all(map(GrammarRule.is_production_rule, rule.pattern))
        elif len(rule.pattern) == 1:
            return not GrammarRule.is_production_rule(rule.pattern[0])
        else:
            return False

    def rule_for_literal(self, literal : str) -> GrammarRule:
        existing_rule = self.literal_tokens.get(literal, None)
        if existing_rule is None:
            new_rule = GrammarRule(f"_TOKENS{self.n_literal_tokens}_", literal, "none")
            self.literal_tokens[literal] = new_rule
            self.n_literal_tokens += 1
            self.rules.append(new_rule)

            return new_rule

        return existing_rule

    def rule_for_connector(self, ruleA : str, ruleB : str, name=None):
        # don't look up if it's a named rule
        existing_rule = None
        key = None
        if name is None:
            key = f"{ruleA}:{ruleB}"
            existing_rule = self.connectors.get(key, None)

        if existing_rule is None:
            pattern = f"{ruleA} {ruleB}"
            if name is None:
                name = f"_CONNECTOR{self.n_connector_rules}_"

            new_connector = GrammarRule(name, pattern, "pool")
            self.n_connector_rules += 1

            if key is not None:
                self.connectors[key] = new_connector

            self.rules.append(new_connector)

            return new_connector

        return existing_rule

    def _handle_single_prod_rule_case(self, rule : GrammarRule):
        substitute_name = rule.pattern[0]
        substitutions = [r for r in self.original_cfg.rules if r.parent == substitute_name]

        for rule_to_sub in substitutions:
            pattern_to_sub = " ".join(rule_to_sub.pattern)
            steps_to_reverse_both_rules = [*rule_to_sub.reverse_with, *rule.reverse_with]
            
            temp_rule = GrammarRule(rule.parent, pattern_to_sub, steps_to_reverse_both_rules)
            
            # TODO: this is terrible, but it works because temp_rules don't really exist
            # but must transfer the properties of the rule we substitute in to create them
            temp_rule.guid = rule_to_sub.guid
            self._expand_rule(temp_rule)

    def _expand_rule(self, rule : GrammarRule):
        if CFGNormalizer.is_cnf_rule(rule):
            self.rules.append(GrammarRule(rule.parent, " ".join(rule.pattern), rule.reverse_with))
            return
        
        if len(rule.pattern) == 1:
            self._handle_single_prod_rule_case(rule)
            return

        working_pattern = [part if GrammarRule.is_production_rule(part) 
            else self.rule_for_literal(part).parent
            for part in rule.pattern]

        while len(working_pattern) > 2:
            ruleB = working_pattern.pop()
            ruleA = working_pattern.pop()

            connector = self.rule_for_connector(ruleA, ruleB)
            working_pattern.append(connector.parent)

        ruleB = working_pattern.pop()
        ruleA = working_pattern.pop()

        connector = self.rule_for_connector(ruleA, ruleB, name=rule.parent)
        connector.reverse_with.extend(rule.reverse_with)

        connector.build_guids.append(rule.guid)

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

        return [newnode.plural(build_name, flattened_components)]

    @classmethod
    def reverse_with_pass(cls, components : list) -> list:
        return components

    def _recursive_descent(self, entry : CYKAlgo.DpTableEntry) -> list:
        if entry.is_main_diagonal:
            astnode = self.astnodes[entry.x]
            if astnode.type == "symbol":
                return []
            elif astnode.type == "keyword" and astnode.op not in Grammar.expressional_keywords:
                return []
            else:
                return [astnode]

        left = self._recursive_descent(entry.get_left_child(self.dp_table))
        right = self._recursive_descent(entry.get_right_child(self.dp_table)) 


        flag = "build="
        components = [left, right]
        for reversal_step in entry.rule.reverse_with:
            if reversal_step == "pass":
                components = AstBuilder.reverse_with_pool(components)
            elif reversal_step == "merge":
                components = AstBuilder.reverse_with_merge(components)
            elif reversal_step == "pool":
                components = AstBuilder.reverse_with_pool(components)
            elif reversal_step[0 : len(flag)] == flag:
                components = AstBuilder.reverse_with_build(reversal_step[len(flag): ], components)

        return components


            


        
